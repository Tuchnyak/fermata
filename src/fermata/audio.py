"""Playing a sound file inside the program, with the `miniaudio` library.

The rest of the program talks to the small `AudioOutput` interface (play a file once or in a
loop, stop it); the tests give it a fake, so they make no sound. `MiniaudioOutput` reads the
file whole, as stereo of 44.1 kHz whatever it is (wav, ogg, flac or mp3: the longest of our
loops decodes in a tenth of a second and takes 21 MB), and plays it on a device of its own, so
that sounds do not cut each other; the sounds end with the program. Anything that goes wrong, such as a file that cannot be
read or no sound system on the machine, means no playback, never an error.
"""

import atexit
from array import array
from collections.abc import Generator
from pathlib import Path
from typing import Protocol

import miniaudio

FORMAT = miniaudio.SampleFormat.SIGNED16
CHANNELS = 2
SAMPLE_RATE = 44100


class Playback(Protocol):
    def stop(self) -> None: ...


class AudioOutput(Protocol):
    def play(self, file: Path, *, loop: bool = False) -> Playback | None:
        """Start a sound; None if it cannot be played."""
        ...

    def close(self) -> None:
        """Stop every sound that is still playing."""
        ...


def sample_stream(samples: array, loop: bool) -> Generator[array, int, None]:
    """The samples of a sound, as the sound system asks for them.

    The system sends the number of frames it needs (a frame is the samples of all the channels)
    and gets the samples for them. A loop goes round without a gap and always fills what was
    asked for; a sound that is not a loop gives what is left and then ends the stream.
    """
    wanted = yield array("h")  # the stream is started before the first request
    total = len(samples)
    position = 0
    while total:
        count = wanted * CHANNELS
        chunk = array("h")
        while len(chunk) < count:
            if position >= total:
                if not loop:
                    break
                position = 0
            part = min(count - len(chunk), total - position)
            chunk.extend(samples[position : position + part])
            position += part
        if count and not chunk:
            return
        wanted = yield chunk


class _Playback:
    def __init__(self):
        self.device: miniaudio.PlaybackDevice | None = None
        self.finished = False  # the sound ended by itself; set by the audio thread

    @property
    def is_playing(self) -> bool:
        return self.device is not None and not self.finished

    def stop(self) -> None:
        device, self.device = self.device, None
        if device is not None:
            device.close()


def _watched(stream: Generator[array, int, None], playback: _Playback):
    """The stream, noting when it ends. The device is not closed here: that is for the main
    thread, the audio thread must not close its own device."""
    try:
        yield from stream
    finally:
        playback.finished = True


class MiniaudioOutput:
    def __init__(self, backends=None):
        """`backends` limits the sound systems the library may use; the tests give it the null
        device, which plays into nothing."""
        self._backends = backends
        self._playbacks: list[_Playback] = []
        # A device left open would keep the program from ending when it ends without `close`.
        atexit.register(self.close)

    @property
    def playing(self) -> int:
        return sum(1 for playback in self._playbacks if playback.is_playing)

    def play(self, file: Path, *, loop: bool = False) -> Playback | None:
        self._free_the_ended()
        playback = _Playback()
        try:
            decoded = miniaudio.decode_file(
                str(file), output_format=FORMAT, nchannels=CHANNELS, sample_rate=SAMPLE_RATE
            )
            playback.device = miniaudio.PlaybackDevice(
                output_format=FORMAT,
                nchannels=CHANNELS,
                sample_rate=SAMPLE_RATE,
                backends=self._backends,
            )
            stream = _watched(sample_stream(decoded.samples, loop), playback)
            next(stream)
            playback.device.start(stream)
        except (miniaudio.MiniaudioError, OSError):
            playback.stop()
            return None
        self._playbacks.append(playback)
        return playback

    def close(self) -> None:
        """Stop every sound that is still playing."""
        for playback in self._playbacks:
            playback.stop()
        self._playbacks.clear()

    def _free_the_ended(self) -> None:
        for playback in self._playbacks:
            if playback.finished:
                playback.stop()
        self._playbacks = [playback for playback in self._playbacks if playback.device is not None]

"""The background sound of a work interval: ticking, white noise or rain, in a loop.

It plays while a work interval is running and is silent at every other time: idle, waiting for
confirmation, in a break, paused. The choice and the switch of the sounds are read at every
`update`, so a change applies at once. The loop is played inside the program (see `audio.py`),
so it ends with the program, and anything that goes wrong, such as no file or no sound system,
only means silence. The files are in `sounds/` (see `sound.py`), named like the choices:
`rain.wav`.
"""

from collections.abc import Callable
from pathlib import Path

from fermata.audio import AudioOutput, Playback
from fermata.engine import Engine
from fermata.intervals import IntervalKind
from fermata.sound import SOUNDS_DIR, sound_files
from fermata.storage.settings import Settings


class BackgroundSound:
    def __init__(
        self,
        engine: Engine,
        get_settings: Callable[[], Settings],
        sounds_dir: Path = SOUNDS_DIR,
        output: AudioOutput | None = None,
    ):
        self._engine = engine
        self._get_settings = get_settings
        self._sounds_dir = sounds_dir
        self._output = output
        self._wanted: str | None = None  # what has been started, even if nothing came of it
        self._playback: Playback | None = None

    def update(self) -> None:
        """Start, replace or stop the sound, as the timer and the settings now call for."""
        wanted = self._sound_called_for()
        if wanted == self._wanted:
            return
        self.stop()
        self._wanted = wanted
        if wanted is not None:
            self._start(wanted)

    def stop(self) -> None:
        self._wanted = None
        playback, self._playback = self._playback, None
        if playback is not None:
            playback.stop()

    def _sound_called_for(self) -> str | None:
        settings = self._get_settings()
        interval = self._engine.current_interval
        if not settings.sound or settings.background_sound == "off":
            return None
        if interval is None or interval.kind != IntervalKind.WORK or self._engine.is_paused:
            return None
        return settings.background_sound

    def _start(self, name: str) -> None:
        files = sound_files(self._sounds_dir, name)
        if not files or self._output is None:
            return
        self._playback = self._output.play(files[0], loop=True)

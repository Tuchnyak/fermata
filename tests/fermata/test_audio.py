import time
import wave
from array import array

import miniaudio
import pytest
from fermata.audio import MiniaudioOutput, sample_stream

# --- the frames of a sound, as the sound system asks for them ----------------------
# A sound is stereo: two samples make a frame, and the system asks for a number of frames.


def stereo(frames):
    """A sound of the given number of frames in which every sample is its own number."""
    return array("h", range(frames * 2))


def start(stream):
    next(stream)  # the system starts the stream before it asks for the first frames
    return stream


def take(stream, requests):
    """What the stream gives, in the order it is given, for these requests (in frames)."""
    taken = array("h")
    for frames in requests:
        try:
            taken.extend(stream.send(frames))
        except StopIteration:
            break
    return taken


def test_a_sound_is_given_once_in_the_order_it_is_stored():
    samples = stereo(10)

    taken = take(start(sample_stream(samples, loop=False)), [3, 3, 3, 3, 3])

    assert taken == samples


def test_no_chunk_is_larger_than_what_was_asked_for():
    stream = start(sample_stream(stereo(10), loop=False))

    for frames in (4, 1, 3):
        assert len(stream.send(frames)) <= frames * 2


def test_a_sound_that_is_over_ends_the_stream():
    stream = start(sample_stream(stereo(4), loop=False))
    stream.send(10)  # more than there is: the rest, and the sound is over

    with pytest.raises(StopIteration):
        stream.send(10)


def test_an_empty_sound_ends_at_once():
    stream = start(sample_stream(array("h"), loop=False))

    with pytest.raises(StopIteration):
        stream.send(10)


def test_a_loop_goes_round_without_a_gap():
    samples = stereo(5)
    requests = [3, 4, 2, 7, 1, 6]  # the wraps fall in the middle of the requests

    taken = take(start(sample_stream(samples, loop=True)), requests)

    expected = array("h")
    while len(expected) < sum(requests) * 2:
        expected.extend(samples)
    assert taken == expected[: sum(requests) * 2]


def test_a_loop_always_fills_what_was_asked_for():
    stream = start(sample_stream(stereo(5), loop=True))

    for frames in (3, 4, 2, 7, 1, 100):
        assert len(stream.send(frames)) == frames * 2


def test_a_loop_of_one_frame_goes_on():
    stream = start(sample_stream(array("h", [7, 8]), loop=True))

    assert list(stream.send(3)) == [7, 8, 7, 8, 7, 8]


def test_an_empty_loop_ends_instead_of_going_round_for_ever():
    stream = start(sample_stream(array("h"), loop=True))

    with pytest.raises(StopIteration):
        stream.send(10)


# --- the output, played into the null device of the library: no sound is made -------


def write_wav(path, seconds, rate=44100, channels=2):
    with wave.open(str(path), "wb") as file:
        file.setnchannels(channels)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(b"\x00\x10" * channels * int(rate * seconds))
    return path


def wait_until(condition, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


@pytest.fixture
def real_output():
    output = MiniaudioOutput(backends=[miniaudio.Backend.NULL])
    yield output
    output.close()


def test_a_sound_plays_and_is_freed_when_it_ends(real_output, tmp_path):
    playback = real_output.play(write_wav(tmp_path / "a.wav", 0.4))

    assert playback is not None
    assert real_output.playing == 1
    assert wait_until(lambda: real_output.playing == 0)


def test_a_loop_goes_on_until_it_is_stopped(real_output, tmp_path):
    playback = real_output.play(write_wav(tmp_path / "a.wav", 0.1), loop=True)

    time.sleep(0.5)  # five times the length of the sound
    assert real_output.playing == 1

    playback.stop()
    assert real_output.playing == 0


def test_stopping_twice_does_no_harm(real_output, tmp_path):
    playback = real_output.play(write_wav(tmp_path / "a.wav", 0.4))

    playback.stop()
    playback.stop()

    assert real_output.playing == 0


def test_stopping_a_sound_that_is_over_does_no_harm(real_output, tmp_path):
    playback = real_output.play(write_wav(tmp_path / "a.wav", 0.1))
    wait_until(lambda: real_output.playing == 0)

    playback.stop()


def test_two_sounds_play_together_and_one_can_be_stopped_alone(real_output, tmp_path):
    loop = real_output.play(write_wav(tmp_path / "loop.wav", 0.1), loop=True)
    real_output.play(write_wav(tmp_path / "signal.wav", 3.0))
    assert real_output.playing == 2

    loop.stop()

    assert real_output.playing == 1


def test_closing_the_output_stops_every_sound(tmp_path):
    output = MiniaudioOutput(backends=[miniaudio.Backend.NULL])
    output.play(write_wav(tmp_path / "a.wav", 0.1), loop=True)
    output.play(write_wav(tmp_path / "b.wav", 0.1), loop=True)

    output.close()

    assert output.playing == 0


def test_a_sound_of_another_rate_and_channels_is_converted(real_output, tmp_path):
    mono = write_wav(tmp_path / "mono.wav", 0.2, rate=22050, channels=1)

    assert real_output.play(mono) is not None


def test_a_missing_file_gives_no_playback(real_output, tmp_path):
    assert real_output.play(tmp_path / "nowhere.wav") is None


def test_a_file_that_is_not_a_sound_gives_no_playback(real_output, tmp_path):
    garbage = tmp_path / "garbage.wav"
    garbage.write_bytes(b"this is not a sound")

    assert real_output.play(garbage) is None


def test_a_machine_without_a_sound_system_gives_no_playback(tmp_path, monkeypatch):
    def no_device(*arguments, **keywords):
        raise miniaudio.MiniaudioError("no sound system")

    monkeypatch.setattr(miniaudio, "PlaybackDevice", no_device)
    output = MiniaudioOutput()

    assert output.play(write_wav(tmp_path / "a.wav", 0.1)) is None
    assert output.playing == 0


def test_a_sound_that_ended_does_not_pile_up_devices(real_output, tmp_path):
    first = write_wav(tmp_path / "a.wav", 0.05)
    for _ in range(3):
        real_output.play(first)
        wait_until(lambda: real_output.playing == 0)

    assert real_output.playing == 0


# --- the end of the program ---------------------------------------------------------


def test_a_program_that_ends_with_a_sound_playing_does_not_hang(tmp_path):
    """A device left open by a program that ends without closing it must not keep it alive."""
    import subprocess
    import sys

    sound = write_wav(tmp_path / "loop.wav", 0.1)
    script = (
        "import miniaudio, pathlib, time\n"
        "from fermata.audio import MiniaudioOutput\n"
        "output = MiniaudioOutput(backends=[miniaudio.Backend.NULL])\n"
        f"output.play(pathlib.Path({str(sound)!r}), loop=True)\n"
        "time.sleep(0.3)\n"
    )

    finished = subprocess.run([sys.executable, "-c", script], timeout=10, check=False)

    assert finished.returncode == 0

from datetime import UTC, datetime, timedelta

import pytest
from fermata import i18n


class FakeClock:
    """A clock that moves only when a test says so."""

    def __init__(self):
        self._now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture(autouse=True)
def silent_application(monkeypatch, tmp_path_factory):
    """No test plays a real sound: the application built in a test looks for its sounds in an
    empty directory. A test of sound passes its own player or sounds directory."""
    monkeypatch.setattr("fermata.wiring.SOUNDS_DIR", tmp_path_factory.mktemp("no_sounds"))


@pytest.fixture(autouse=True)
def english_language():
    """Every test starts in English, whatever language the one before it chose."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


class FakePlayback:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeOutput:
    """Stands in for the audio output: remembers what it was asked to play, plays nothing."""

    def __init__(self, fails=False):
        self.fails = fails  # a machine with no sound system: nothing can be played
        self.plays = []  # (file, loop)
        self.playbacks = []

    def play(self, file, *, loop=False):
        self.plays.append((file, loop))
        if self.fails:
            return None
        playback = FakePlayback()
        self.playbacks.append(playback)
        return playback

    def close(self):
        for playback in self.playbacks:
            playback.stop()

    @property
    def files(self):
        return [file for file, _ in self.plays]

    @property
    def running(self):
        return [playback for playback in self.playbacks if not playback.stopped]


@pytest.fixture
def output():
    return FakeOutput()


@pytest.fixture
def silent_output():
    """A machine with no sound system."""
    return FakeOutput(fails=True)

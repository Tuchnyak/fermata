from datetime import UTC, datetime, timedelta

import pytest


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
    monkeypatch.setattr("timer.wiring.SOUNDS_DIR", tmp_path_factory.mktemp("no_sounds"))

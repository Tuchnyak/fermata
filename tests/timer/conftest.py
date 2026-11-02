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

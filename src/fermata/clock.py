"""The clock of the application: the real one, and a sped-up one for testing in development."""

from collections.abc import Callable
from datetime import UTC, datetime

DEV_SPEED = 2  # how many times faster the clock of a run from source goes


def real_clock() -> datetime:
    return datetime.now(UTC)


def speed_of(*, release: bool, real_time: bool) -> int:
    """How many times faster than the real one the clock goes: only a run from source is sped
    up, unless it is asked for the normal speed."""
    return 1 if release or real_time else DEV_SPEED


def sped_up_clock(
    speed: int, source: Callable[[], datetime] = real_clock
) -> Callable[[], datetime]:
    """A clock that starts at the time of its source and then runs `speed` times faster."""
    started = source()

    def clock() -> datetime:
        return started + (source() - started) * speed

    return clock


def make_clock(
    *, release: bool, real_time: bool, source: Callable[[], datetime] = real_clock
) -> Callable[[], datetime]:
    speed = speed_of(release=release, real_time=real_time)
    if speed == 1:
        return source
    return sped_up_clock(speed, source)

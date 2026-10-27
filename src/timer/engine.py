"""The timer engine: runs intervals against an injected clock.

Pure logic: no UI and no database. The clock is a function returning the current time, and
the engine never counts ticks: the remaining time is always computed from the clock, so
`tick()` may be called as often or as rarely as the caller likes. Settings are read through
`get_settings` each time an interval starts, so a change applies only to later intervals.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from timer.intervals import (
    FinishedInterval,
    IntervalKind,
    IntervalStatus,
    RunningInterval,
    planned_seconds,
)
from timer.storage.settings import Settings


class Engine:
    def __init__(
        self, get_settings: Callable[[], Settings], clock: Callable[[], datetime]
    ):
        self._get_settings = get_settings
        self._clock = clock
        self._current_interval: RunningInterval | None = None
        self._finished_intervals: list[FinishedInterval] = []
        self._paused_at: datetime | None = None
        self._paused_seconds = 0.0  # the pauses already over, in the current interval

    @property
    def current_interval(self) -> RunningInterval | None:
        """The interval that is running now, or None."""
        return self._current_interval

    @property
    def finished_intervals(self) -> list[FinishedInterval]:
        """The intervals that have ended, in order. Provides copy of a list."""
        return list(self._finished_intervals)

    @property
    def is_paused(self) -> bool:
        return self._paused_at is not None

    def pause(self) -> None:
        if self._current_interval is None or self.is_paused:
            return
        self._paused_at = self._clock()

    def resume(self) -> None:
        if self._paused_at is None:
            return
        pause_delta = self._clock() - self._paused_at
        self._paused_seconds += pause_delta.total_seconds()
        self._paused_at = None

    def start_flow(self, category_id: int) -> None:
        settings = self._get_settings()
        self._current_interval = RunningInterval(
            kind=IntervalKind.WORK,
            category_id=category_id,
            planned_seconds=planned_seconds(IntervalKind.WORK, settings),
            started_at=self._clock(),
        )
        self._clear_pauses()

    def remaining_seconds(self) -> float:
        """Seconds left in the running interval; 0 when nothing is running.

        Time spent paused is not counted as worked, so the value stands still on a pause.
        """
        if self._current_interval is None:
            return 0.0
        interval = self._current_interval
        counted_until = self._paused_at if self._paused_at is not None else self._clock()
        time_delta = counted_until - interval.started_at
        worked_seconds = time_delta.total_seconds() - self._paused_seconds
        return interval.planned_seconds - worked_seconds

    def tick(self) -> None:
        """Finish the running interval if its time has elapsed."""
        if self._current_interval is None:
            return
        if self.remaining_seconds() > 0:
            return
        self._complete_current_interval()

    def _complete_current_interval(self) -> None:
        interval = self._current_interval
        assert interval is not None
        # The end is calculated, not read from the clock: a late tick must not stretch it.
        interval_seconds = interval.planned_seconds + self._paused_seconds
        ended_at = interval.started_at + timedelta(seconds=interval_seconds)
        self._finished_intervals.append(
            FinishedInterval(
                kind=interval.kind,
                category_id=interval.category_id,
                planned_seconds=interval.planned_seconds,
                started_at=interval.started_at,
                ended_at=ended_at,
                actual_seconds=interval.planned_seconds,
                status=IntervalStatus.COMPLETED,
            )
        )
        self._current_interval = None
        self._clear_pauses()

    def _clear_pauses(self) -> None:
        self._paused_at = None
        self._paused_seconds = 0.0

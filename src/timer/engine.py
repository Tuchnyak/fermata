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
    next_kind,
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
        self._flow_category_id: int | None = None
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
        self._flow_category_id = category_id
        self._finished_intervals = []
        self._begin_interval(IntervalKind.WORK, category_id, self._get_settings())

    def skip(self) -> None:
        """End the running interval early and start the next one at once."""
        if self._current_interval is None:
            return
        self._end_current_interval_early(IntervalStatus.SKIPPED)
        self._begin_next_interval()

    def stop(self) -> None:
        """End the running interval early and the flow with it."""
        if self._current_interval is None:
            return
        self._end_current_interval_early(IntervalStatus.STOPPED)

    def remaining_seconds(self) -> float:
        """Seconds left in the running interval; 0 when nothing is running.

        Time spent paused is not counted as worked, so the value stands still on a pause.
        """
        if self._current_interval is None:
            return 0.0
        return self._current_interval.planned_seconds - self._worked_seconds(
            self._current_interval
        )

    def tick(self) -> None:
        """Finish the running interval if its time has elapsed."""
        if self._current_interval is None:
            return
        if self.remaining_seconds() > 0:
            return
        self._complete_current_interval()

    def _worked_seconds(self, interval: RunningInterval) -> float:
        counted_until = self._paused_at if self._paused_at is not None else self._clock()
        time_delta = counted_until - interval.started_at
        return time_delta.total_seconds() - self._paused_seconds

    def _begin_next_interval(self) -> None:
        finished_kinds = [interval.kind for interval in self._finished_intervals]
        settings = self._get_settings()
        kind = next_kind(finished_kinds, settings)
        category_id = self._flow_category_id if kind == IntervalKind.WORK else None
        self._begin_interval(kind, category_id, settings)

    def _begin_interval(
        self, kind: IntervalKind, category_id: int | None, settings: Settings
    ) -> None:
        self._current_interval = RunningInterval(
            kind=kind,
            category_id=category_id,
            planned_seconds=planned_seconds(kind, settings),
            started_at=self._clock(),
        )
        self._clear_pauses()

    def _end_current_interval_early(self, status: IntervalStatus) -> None:
        interval = self._current_interval
        assert interval is not None
        worked_seconds = min(int(self._worked_seconds(interval)), interval.planned_seconds)
        self._finish_current_interval(
            status, ended_at=self._clock(), actual_seconds=worked_seconds
        )

    def _complete_current_interval(self) -> None:
        interval = self._current_interval
        assert interval is not None
        # The end is calculated, not read from the clock: a late tick must not stretch it.
        interval_seconds = interval.planned_seconds + self._paused_seconds
        ended_at = interval.started_at + timedelta(seconds=interval_seconds)
        self._finish_current_interval(
            IntervalStatus.COMPLETED,
            ended_at=ended_at,
            actual_seconds=interval.planned_seconds,
        )

    def _finish_current_interval(
        self, status: IntervalStatus, ended_at: datetime, actual_seconds: int
    ) -> None:
        interval = self._current_interval
        assert interval is not None
        self._finished_intervals.append(
            FinishedInterval(
                kind=interval.kind,
                category_id=interval.category_id,
                planned_seconds=interval.planned_seconds,
                started_at=interval.started_at,
                ended_at=ended_at,
                actual_seconds=actual_seconds,
                status=status,
            )
        )
        self._current_interval = None
        self._clear_pauses()

    def _clear_pauses(self) -> None:
        self._paused_at = None
        self._paused_seconds = 0.0

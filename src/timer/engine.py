"""The timer engine: runs intervals against an injected clock.

Pure logic: no UI and no database. The clock is a function returning the current time, and
the engine never counts ticks: the remaining time is always computed from the clock, so
`tick()` may be called as often or as rarely as the caller likes. Settings are read through
`get_settings` each time an interval starts, so a change applies only to later intervals.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from timer.intervals import (
    BaseInterval,
    FinishedInterval,
    IntervalKind,
    IntervalStatus,
    RunningInterval,
    next_kind,
    planned_seconds,
)
from timer.storage.settings import Settings


@dataclass(frozen=True)
class FlowEvent:
    """What one engine step changed, reported to the listener as a unit."""

    at: datetime
    flow_started: bool = False
    finished_interval: FinishedInterval | None = None
    started_interval: RunningInterval | None = None
    flow_ended: bool = False


class Engine:
    def __init__(
        self,
        get_settings: Callable[[], Settings],
        clock: Callable[[], datetime],
        on_flow_event: Callable[[FlowEvent], None] | None = None,
    ):
        self._get_settings = get_settings
        self._clock = clock
        self._on_flow_event = on_flow_event
        self._current_interval: RunningInterval | None = None
        self._finished_intervals: list[FinishedInterval] = []
        self._flow_category_id: int | None = None
        self._is_waiting = False  # an interval has ended and `confirm()` is awaited
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
    def upcoming_interval(self) -> BaseInterval | None:
        """The interval that `confirm()` would start, or None if the engine is not waiting.

        Worked out from the settings of the moment, so a change made while waiting applies.
        """
        if not self._is_waiting:
            return None
        return self._plan_next_interval()

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
        work_seconds = planned_seconds(IntervalKind.WORK, self._get_settings())
        self._begin_interval(BaseInterval(IntervalKind.WORK, category_id, work_seconds))
        self._emit(flow_started=True, started_interval=self._current_interval)

    def confirm(self) -> None:
        """Start the upcoming interval; does nothing unless the engine is waiting."""
        if not self._is_waiting:
            return
        self._begin_interval(self._plan_next_interval())
        self._emit(started_interval=self._current_interval)

    def skip(self) -> None:
        """End the running interval early and start the next one at once."""
        if self._current_interval is None:
            return
        self._end_current_interval_early(IntervalStatus.SKIPPED)
        self._begin_interval(self._plan_next_interval())
        self._emit(
            finished_interval=self._finished_intervals[-1],
            started_interval=self._current_interval,
        )

    def stop(self) -> None:
        """End the running interval early and the flow with it."""
        was_waiting = self._is_waiting
        self._is_waiting = False
        if self._current_interval is not None:
            self._end_current_interval_early(IntervalStatus.STOPPED)
            self._emit(finished_interval=self._finished_intervals[-1], flow_ended=True)
        elif was_waiting:
            self._emit(flow_ended=True)

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
        self._emit(
            finished_interval=self._finished_intervals[-1],
            started_interval=self._current_interval,
        )

    def _emit(
        self,
        *,
        flow_started: bool = False,
        finished_interval: FinishedInterval | None = None,
        started_interval: RunningInterval | None = None,
        flow_ended: bool = False,
    ) -> None:
        if self._on_flow_event is None:
            return
        self._on_flow_event(
            FlowEvent(
                at=self._clock(),
                flow_started=flow_started,
                finished_interval=finished_interval,
                started_interval=started_interval,
                flow_ended=flow_ended,
            )
        )

    def _worked_seconds(self, interval: RunningInterval) -> float:
        counted_until = self._paused_at if self._paused_at is not None else self._clock()
        time_delta = counted_until - interval.started_at
        return time_delta.total_seconds() - self._paused_seconds

    def _plan_next_interval(self) -> BaseInterval:
        finished_kinds = [interval.kind for interval in self._finished_intervals]
        settings = self._get_settings()
        kind = next_kind(finished_kinds, settings)
        category_id = self._flow_category_id if kind == IntervalKind.WORK else None
        return BaseInterval(kind, category_id, planned_seconds(kind, settings))

    def _begin_interval(self, plan: BaseInterval) -> None:
        self._current_interval = RunningInterval(
            kind=plan.kind,
            category_id=plan.category_id,
            planned_seconds=plan.planned_seconds,
            started_at=self._clock(),
        )
        self._is_waiting = False
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
        if self._next_interval_starts_by_itself(interval.kind):
            self._begin_interval(self._plan_next_interval())
        else:
            self._is_waiting = True

    def _next_interval_starts_by_itself(self, completed_kind: IntervalKind) -> bool:
        transition_mode = self._get_settings().transition_mode
        if transition_mode == "auto":
            return True
        if transition_mode == "mixed":
            return completed_kind == IntervalKind.WORK
        return False

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

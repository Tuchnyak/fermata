"""Interval kinds and the rules of their sequence: what comes next and how long it lasts.

Pure logic: no clock and no database. The kinds are the same texts that the `interval` table
stores in its `kind` column (see docs/schema.md).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from timer.storage.settings import Settings


class IntervalKind(StrEnum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class IntervalStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    STOPPED = "stopped"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class BaseInterval:
    kind: IntervalKind
    category_id: int | None
    planned_seconds: int


@dataclass(frozen=True)
class RunningInterval(BaseInterval):
    started_at: datetime


@dataclass(frozen=True)
class FinishedInterval(BaseInterval):
    started_at: datetime
    ended_at: datetime
    actual_seconds: int
    status: IntervalStatus


@dataclass(frozen=True)
class IntervalEntity(BaseInterval):
    """An interval as stored in the database; unfinished fields are None while it runs."""

    id: int
    position: int
    started_at: datetime
    actual_seconds: int | None
    ended_at: datetime | None
    status: IntervalStatus | None


def next_kind(finished: Sequence[IntervalKind], settings: Settings) -> IntervalKind:
    """Return the kind of the interval that follows the finished ones of a session.

    Only kinds are given, not how an interval ended, so a skipped work interval counts
    toward `long_break_every` like a completed one.
    """
    if not finished or finished[-1] != IntervalKind.WORK:
        return IntervalKind.WORK

    work_interval_count = finished.count(IntervalKind.WORK)
    if work_interval_count % settings.long_break_every == 0:
        return IntervalKind.LONG_BREAK
    return IntervalKind.SHORT_BREAK


def planned_seconds(kind: IntervalKind, settings: Settings) -> int:
    """Return the length in seconds that the settings give to an interval of this kind."""
    if kind == IntervalKind.WORK:
        minutes = settings.work_minutes
    elif kind == IntervalKind.SHORT_BREAK:
        minutes = settings.short_break_minutes
    else:
        minutes = settings.long_break_minutes
    return minutes * 60


@dataclass(frozen=True)
class SessionSummary:
    """How a scenario session went: its work intervals done and skipped."""

    done_count: int
    skipped_count: int


def summarize(finished: Sequence[FinishedInterval]) -> SessionSummary:
    """Count the work intervals of a session by how they ended; breaks and stops are left out."""
    done_count = 0
    skipped_count = 0
    for interval in finished:
        if interval.kind != IntervalKind.WORK:
            continue
        if interval.status == IntervalStatus.COMPLETED:
            done_count += 1
        elif interval.status == IntervalStatus.SKIPPED:
            skipped_count += 1
    return SessionSummary(done_count, skipped_count)

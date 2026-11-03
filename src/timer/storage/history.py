"""Reading the history: the finished work intervals of a period, as the history screen lists them.

Read only; what is written is in `sessions.py`. See docs/schema.md for the view it reads.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from timer.intervals import IntervalStatus
from timer.storage.db import Db
from timer.storage.sessions import _to_datetime, _to_text


@dataclass(frozen=True)
class HistoryInterval:
    started_at: datetime
    category_name: str
    category_color: str
    actual_seconds: int | None  # None for an interrupted interval: its length is unknown
    status: IntervalStatus


class HistoryRepository:
    def __init__(self, db: Db):
        self._db = db

    def work_intervals(self, start: datetime, end: datetime) -> list[HistoryInterval]:
        """The finished work intervals that started from `start` (included) to `end` (excluded),
        in the order they started."""
        # The times are UTC text of one fixed form, so comparing the text is comparing the times.
        return self._db.query(
            "SELECT started_at, category_name, category_color, actual_seconds, status"
            " FROM interval_details"
            " WHERE kind = 'work' AND status IS NOT NULL"
            " AND started_at >= :start AND started_at < :end"
            " ORDER BY started_at, id",
            {"start": _to_text(start), "end": _to_text(end)},
            mapper=_to_history_interval,
        )


def _to_history_interval(row: sqlite3.Row) -> HistoryInterval:
    return HistoryInterval(
        started_at=_to_datetime(row["started_at"]),
        category_name=row["category_name"],
        category_color=row["category_color"],
        actual_seconds=row["actual_seconds"],
        status=IntervalStatus(row["status"]),
    )

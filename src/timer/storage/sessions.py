"""Storage of sessions and their intervals: the history the timer writes while it runs.

Times are stored as ISO-8601 UTC text with whole seconds, e.g. `2026-10-19T09:00:00Z`
(see docs/schema.md); the repository converts them from and to timezone-aware datetimes.
"""

import sqlite3
from datetime import UTC, datetime
from enum import StrEnum

from timer.intervals import (
    IntervalEntity,
    IntervalKind,
    IntervalStatus,
    RunningInterval,
)
from timer.scenarios import Scenario, to_snapshot
from timer.storage.db import Db


class SessionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    INTERRUPTED = "interrupted"


def _to_text(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_datetime(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _to_interval_entity(row: sqlite3.Row) -> IntervalEntity:
    ended_at = row["ended_at"]
    status = row["status"]
    return IntervalEntity(
        kind=IntervalKind(row["kind"]),
        category_id=row["category_id"],
        planned_seconds=row["planned_seconds"],
        id=row["id"],
        position=row["position"],
        started_at=_to_datetime(row["started_at"]),
        actual_seconds=row["actual_seconds"],
        ended_at=None if ended_at is None else _to_datetime(ended_at),
        status=None if status is None else IntervalStatus(status),
    )


class SessionRepository:
    def __init__(self, db: Db):
        self._db = db

    def create_flow(self, started_at: datetime) -> int:
        session_id = self._db.insert(
            "INSERT INTO session (kind, status, started_at)"
            " VALUES ('flow', :status, :started_at)",
            {"status": SessionStatus.RUNNING, "started_at": _to_text(started_at)},
        )
        assert session_id is not None
        return session_id

    def create_scenario_session(self, started_at: datetime, scenario: Scenario) -> int:
        session_id = self._db.insert(
            "INSERT INTO session (kind, status, started_at, scenario_name, scenario_snapshot)"
            " VALUES ('scenario', :status, :started_at, :name, :snapshot)",
            {
                "status": SessionStatus.RUNNING,
                "started_at": _to_text(started_at),
                "name": scenario.name,
                "snapshot": to_snapshot(scenario),
            },
        )
        assert session_id is not None
        return session_id

    def start_interval(
        self, session_id: int, position: int, interval: RunningInterval
    ) -> int:
        interval_id = self._db.insert(
            "INSERT INTO interval"
            " (session_id, position, kind, category_id, planned_seconds, started_at)"
            " VALUES (:session_id, :position, :kind, :category_id, :planned_seconds,"
            " :started_at)",
            {
                "session_id": session_id,
                "position": position,
                "kind": interval.kind,
                "category_id": interval.category_id,
                "planned_seconds": interval.planned_seconds,
                "started_at": _to_text(interval.started_at),
            },
        )
        assert interval_id is not None
        return interval_id

    def finish_interval(
        self,
        interval_id: int,
        *,
        status: IntervalStatus,
        actual_seconds: int,
        ended_at: datetime,
    ) -> None:
        updated_count = self._db.execute(
            "UPDATE interval SET status = :status, actual_seconds = :actual_seconds,"
            " ended_at = :ended_at WHERE id = :id",
            {
                "status": status,
                "actual_seconds": actual_seconds,
                "ended_at": _to_text(ended_at),
                "id": interval_id,
            },
        )
        if updated_count == 0:
            raise LookupError(f"No interval with id {interval_id}")

    def finish_session(
        self, session_id: int, *, status: SessionStatus, ended_at: datetime
    ) -> None:
        updated_count = self._db.execute(
            "UPDATE session SET status = :status, ended_at = :ended_at WHERE id = :id",
            {"status": status, "ended_at": _to_text(ended_at), "id": session_id},
        )
        if updated_count == 0:
            raise LookupError(f"No session with id {session_id}")

    def interrupt_running_sessions(self) -> None:
        """Mark what an app closed in the middle left running as interrupted.

        The end times stay empty: it is not known when the app was closed.
        """
        parameters = {
            "running": SessionStatus.RUNNING,
            "interrupted": SessionStatus.INTERRUPTED,
        }
        with self._db.transaction():
            self._db.execute(
                "UPDATE interval SET status = :interrupted WHERE status IS NULL"
                " AND session_id IN (SELECT id FROM session WHERE status = :running)",
                parameters,
            )
            self._db.execute(
                "UPDATE session SET status = :interrupted WHERE status = :running",
                parameters,
            )

    def list_intervals(self, session_id: int) -> list[IntervalEntity]:
        return self._db.query(
            "SELECT * FROM interval WHERE session_id = ? ORDER BY position",
            (session_id,),
            mapper=_to_interval_entity,
        )

    def last_flow_category_id(self) -> int | None:
        # A session has no category of its own: take it from the work intervals of the
        # most recent flow.
        return self._db.query_one(
            "SELECT category_id FROM interval"
            " WHERE kind = 'work' AND session_id = ("
            "   SELECT id FROM session WHERE kind = 'flow'"
            "   ORDER BY started_at DESC, id DESC LIMIT 1)"
            " ORDER BY position LIMIT 1",
            mapper=lambda row: row["category_id"],
        )

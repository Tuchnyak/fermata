"""The recorder: writes what the engine does into the database, one transaction per step.

It is given to the engine as its `on_flow_event` listener. The events carry everything one
step changed (e.g. a skip ends an interval and starts the next), so a step is either written
completely or not at all.
"""

from timer.engine import FlowEvent
from timer.storage.db import Db
from timer.storage.sessions import SessionRepository, SessionStatus


class Recorder:
    def __init__(self, db: Db, session_repository: SessionRepository):
        self._db = db
        self._session_repository = session_repository
        self._session_id: int | None = None
        self._interval_id: int | None = None
        self._position = 0  # the position of the last interval started in the session

    def record(self, event: FlowEvent) -> None:
        # The new state is kept in locals and stored only after the transaction has
        # succeeded, so a failed step does not leave the recorder pointing at rows that
        # were rolled back.
        session_id = self._session_id
        interval_id = self._interval_id
        position = self._position

        with self._db.transaction():
            if event.flow_started:
                session_id = self._session_repository.create_flow(event.at)
                position = 0
            assert session_id is not None

            finished = event.finished_interval
            if finished is not None:
                assert interval_id is not None
                self._session_repository.finish_interval(
                    interval_id,
                    status=finished.status,
                    actual_seconds=finished.actual_seconds,
                    ended_at=finished.ended_at,
                )

            started = event.started_interval
            if started is not None:
                position += 1
                interval_id = self._session_repository.start_interval(
                    session_id, position, started
                )

            if event.flow_ended:
                self._session_repository.finish_session(
                    session_id, status=SessionStatus.STOPPED, ended_at=event.at
                )

        self._session_id = session_id
        self._interval_id = interval_id
        self._position = position

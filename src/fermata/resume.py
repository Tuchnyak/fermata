"""Resuming a scenario session that an app closed in the middle (spec section 10).

The session is offered once the startup recovery has marked it interrupted. Yes continues the
same session: the intervals that ended count as they did, the interval that was running is
left interrupted in the history, and the next work interval starts again from the beginning.
No ends the session as stopped.
"""

from fermata.engine import Engine
from fermata.i18n import t
from fermata.intervals import FinishedInterval, IntervalEntity, IntervalKind, IntervalStatus
from fermata.recorder import Recorder
from fermata.storage.sessions import InterruptedSession, SessionRepository


def _to_finished_interval(entity: IntervalEntity) -> FinishedInterval:
    assert entity.status is not None
    assert entity.ended_at is not None and entity.actual_seconds is not None
    return FinishedInterval(
        kind=entity.kind,
        category_id=entity.category_id,
        planned_seconds=entity.planned_seconds,
        started_at=entity.started_at,
        ended_at=entity.ended_at,
        actual_seconds=entity.actual_seconds,
        status=entity.status,
    )


class Resumption:
    def __init__(
        self,
        session_repository: SessionRepository,
        recorder: Recorder,
        engine: Engine,
        interrupted: InterruptedSession,
    ):
        self._session_repository = session_repository
        self._recorder = recorder
        self._engine = engine
        self._interrupted = interrupted

    def question(self) -> str:
        scenario = self._interrupted.scenario
        finished_work_count = 0
        for interval in self._finished_intervals():
            if interval.kind == IntervalKind.WORK:
                finished_work_count += 1
        return t(
            "resume.question",
            name=scenario.name,
            number=finished_work_count + 1,
            total=len(scenario.work_category_ids()),
        )

    def resume(self) -> None:
        session_id = self._interrupted.session_id
        last_position = max(
            (interval.position for interval in self._interrupted.intervals), default=0
        )
        self._session_repository.reopen_session(session_id)
        self._recorder.resume(session_id, last_position)
        self._engine.resume_scenario(self._interrupted.scenario, self._finished_intervals())

    def decline(self) -> None:
        self._session_repository.stop_interrupted_session(self._interrupted.session_id)

    def _finished_intervals(self) -> list[FinishedInterval]:
        """The intervals that ended in the session; one that was running when it closed is not."""
        finished = []
        for entity in self._interrupted.intervals:
            if entity.status in (IntervalStatus.COMPLETED, IntervalStatus.SKIPPED):
                finished.append(_to_finished_interval(entity))
        return finished

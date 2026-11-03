from datetime import UTC, datetime, timedelta

import pytest
from timer.intervals import IntervalKind, IntervalStatus, RunningInterval
from timer.scenarios import Scenario, ScenarioRow
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.history import HistoryInterval, HistoryRepository
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.sessions import SessionRepository, SessionStatus

DAY_START = datetime(2026, 1, 1, tzinfo=UTC)
DAY_END = DAY_START + timedelta(days=1)


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def history_repository(db):
    return HistoryRepository(db)


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def work_id(category_repository):
    return category_repository.create("Work", "#112233").id


@pytest.fixture
def reading_id(category_repository):
    return category_repository.create("Reading", "#445566").id


def at(hour, minute=0, day=1):
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


def record(
    session_repository,
    session_id,
    position,
    started_at,
    *,
    category_id=None,
    kind=IntervalKind.WORK,
    status=IntervalStatus.COMPLETED,
    actual_seconds=25 * 60,
):
    """Store an interval and finish it; with no status it is left running."""
    interval_id = session_repository.start_interval(
        session_id,
        position,
        RunningInterval(
            kind=kind,
            category_id=category_id,
            planned_seconds=25 * 60,
            started_at=started_at,
        ),
    )
    if status is not None:
        session_repository.finish_interval(
            interval_id,
            status=status,
            actual_seconds=actual_seconds,
            ended_at=started_at + timedelta(seconds=actual_seconds or 0),
        )
    return interval_id


def intervals(history_repository, start=DAY_START, end=DAY_END):
    return history_repository.work_intervals(start, end)


# --- what is listed ------------------------------------------------------------


def test_nothing_is_listed_when_nothing_was_recorded(history_repository):
    assert intervals(history_repository) == []


def test_a_work_interval_is_listed_with_its_category_and_outcome(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)

    assert intervals(history_repository) == [
        HistoryInterval(
            started_at=at(9),
            category_name="Work",
            category_color="#112233",
            actual_seconds=25 * 60,
            status=IntervalStatus.COMPLETED,
        )
    ]


@pytest.mark.parametrize(
    "status", [IntervalStatus.COMPLETED, IntervalStatus.SKIPPED, IntervalStatus.STOPPED]
)
def test_a_finished_interval_of_every_status_is_listed(
    history_repository, session_repository, work_id, status
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id, status=status, actual_seconds=600)

    (listed,) = intervals(history_repository)

    assert listed.status == status
    assert listed.actual_seconds == 600


def test_an_interrupted_interval_is_listed_without_a_duration(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(
        session_repository, session_id, 1, at(9), category_id=work_id,
        status=IntervalStatus.INTERRUPTED, actual_seconds=None,
    )

    (listed,) = intervals(history_repository)

    assert listed.status == IntervalStatus.INTERRUPTED
    assert listed.actual_seconds is None


def test_breaks_are_not_listed(history_repository, session_repository, work_id):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)
    record(session_repository, session_id, 2, at(9, 25), kind=IntervalKind.SHORT_BREAK)
    record(session_repository, session_id, 3, at(10), kind=IntervalKind.LONG_BREAK)

    assert [row.started_at for row in intervals(history_repository)] == [at(9)]


def test_an_interval_that_is_still_running_is_not_listed(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id, status=None)

    assert intervals(history_repository) == []


def test_intervals_of_flows_and_of_scenarios_are_listed_alike(
    history_repository, session_repository, work_id
):
    flow_id = session_repository.create_flow(at(9))
    record(session_repository, flow_id, 1, at(9), category_id=work_id)
    scenario = Scenario("Day", (ScenarioRow(work_id, 1),))
    scenario_session_id = session_repository.create_scenario_session(at(10), scenario)
    record(session_repository, scenario_session_id, 1, at(10), category_id=work_id)

    assert [row.started_at for row in intervals(history_repository)] == [at(9), at(10)]


def test_the_intervals_of_a_stopped_or_interrupted_session_are_listed_too(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)
    session_repository.finish_session(session_id, status=SessionStatus.STOPPED, ended_at=at(10))

    assert len(intervals(history_repository)) == 1


# --- the period and the order --------------------------------------------------


def test_the_intervals_are_listed_in_the_order_they_started(
    history_repository, session_repository, work_id, reading_id
):
    first = session_repository.create_flow(at(8))
    second = session_repository.create_flow(at(7))  # a session created earlier may run later
    record(session_repository, first, 1, at(11), category_id=work_id)
    record(session_repository, second, 1, at(8), category_id=reading_id)
    record(session_repository, first, 2, at(9, 30), category_id=work_id)

    assert [row.started_at for row in intervals(history_repository)] == [
        at(8),
        at(9, 30),
        at(11),
    ]


def test_the_start_of_the_period_is_included_and_its_end_is_not(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(0))
    record(session_repository, session_id, 1, DAY_START, category_id=work_id)
    record(session_repository, session_id, 2, DAY_END - timedelta(seconds=1), category_id=work_id)
    record(session_repository, session_id, 3, DAY_END, category_id=work_id)
    record(session_repository, session_id, 4, DAY_START - timedelta(seconds=1), category_id=work_id)

    assert [row.started_at for row in intervals(history_repository)] == [
        DAY_START,
        DAY_END - timedelta(seconds=1),
    ]


def test_an_interval_that_runs_past_the_end_belongs_to_the_period_it_started_in(
    history_repository, session_repository, work_id
):
    session_id = session_repository.create_flow(at(23))
    record(session_repository, session_id, 1, at(23, 50), category_id=work_id, actual_seconds=25 * 60)

    assert len(intervals(history_repository)) == 1
    assert intervals(history_repository, DAY_END, DAY_END + timedelta(days=1)) == []


def test_the_bounds_may_be_given_in_any_time_zone(
    history_repository, session_repository, work_id
):
    from datetime import timezone

    moscow = timezone(timedelta(hours=3))
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)  # 12:00 in Moscow

    start = datetime(2026, 1, 1, tzinfo=moscow)  # 21:00 on 31 Dec in UTC
    assert len(history_repository.work_intervals(start, start + timedelta(days=1))) == 1


# --- the category --------------------------------------------------------------


def test_a_renamed_category_shows_its_new_name(
    history_repository, session_repository, category_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)

    category_repository.update(work_id, name="Deep work", color="#abcdef")

    (listed,) = intervals(history_repository)
    assert (listed.category_name, listed.category_color) == ("Deep work", "#abcdef")


def test_an_archived_category_is_still_shown(
    history_repository, session_repository, category_repository, work_id
):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=work_id)

    category_repository.archive(work_id)

    assert [row.category_name for row in intervals(history_repository)] == ["Work"]


def test_the_system_category_is_listed_as_none(history_repository, session_repository):
    session_id = session_repository.create_flow(at(9))
    record(session_repository, session_id, 1, at(9), category_id=1)

    (listed,) = intervals(history_repository)

    assert (listed.category_name, listed.category_color) == ("None", "#9e9e9e")

from datetime import UTC, datetime, timedelta, timezone

import pytest
from timer.intervals import (
    IntervalEntity,
    IntervalKind,
    IntervalStatus,
    RunningInterval,
)
from timer.scenarios import Scenario, ScenarioRow, from_snapshot
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.sessions import SessionRepository, SessionStatus

STARTED = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LATER = STARTED + timedelta(minutes=25)


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def work_category_id(category_repository):
    return category_repository.create("Work", "#112233").id


@pytest.fixture
def reading_category_id(category_repository):
    return category_repository.create("Reading", "#445566").id


def work_interval(category_id, started_at=STARTED):
    return RunningInterval(
        kind=IntervalKind.WORK,
        category_id=category_id,
        planned_seconds=25 * 60,
        started_at=started_at,
    )


def short_break(started_at=LATER):
    return RunningInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=started_at,
    )


def stored_session(db, session_id):
    return db.query_one("SELECT * FROM session WHERE id = ?", (session_id,), mapper=dict)


# --- create_flow -------------------------------------------------------------


def test_a_created_flow_is_stored_as_a_running_flow_session(db, session_repository):
    session_id = session_repository.create_flow(STARTED)

    session = stored_session(db, session_id)
    assert session["kind"] == "flow"
    assert session["status"] == "running"
    assert session["started_at"] == "2026-01-01T12:00:00Z"
    assert session["ended_at"] is None
    assert session["scenario_name"] is None
    assert session["scenario_snapshot"] is None


def test_every_session_gets_its_own_id(session_repository):
    first = session_repository.create_flow(STARTED)
    second = session_repository.create_flow(LATER)

    assert first != second


def test_times_are_stored_as_utc_text_without_fractions(db, session_repository):
    moscow = timezone(timedelta(hours=3))
    started_at = datetime(2026, 1, 1, 15, 0, 0, 123456, tzinfo=moscow)

    session_id = session_repository.create_flow(started_at)

    assert stored_session(db, session_id)["started_at"] == "2026-01-01T12:00:00Z"


@pytest.mark.parametrize("status", list(SessionStatus))
def test_the_session_table_accepts_every_session_status(db, status):
    db.execute(
        "INSERT INTO session (kind, status, started_at) VALUES ('flow', :status, :started_at)",
        {"status": status, "started_at": "2026-01-01T12:00:00Z"},
    )

    assert db.query_one("SELECT status FROM session", mapper=lambda row: row[0]) == status


# --- start_interval ----------------------------------------------------------


def test_a_started_work_interval_is_stored_as_running(
    session_repository, work_category_id
):
    session_id = session_repository.create_flow(STARTED)

    interval_id = session_repository.start_interval(
        session_id, 1, work_interval(work_category_id)
    )

    assert session_repository.list_intervals(session_id) == [
        IntervalEntity(
            kind=IntervalKind.WORK,
            category_id=work_category_id,
            planned_seconds=25 * 60,
            id=interval_id,
            position=1,
            started_at=STARTED,
            actual_seconds=None,
            ended_at=None,
            status=None,
        )
    ]


def test_a_started_break_is_stored_without_a_category(session_repository):
    session_id = session_repository.create_flow(STARTED)

    interval_id = session_repository.start_interval(session_id, 1, short_break())

    assert session_repository.list_intervals(session_id) == [
        IntervalEntity(
            kind=IntervalKind.SHORT_BREAK,
            category_id=None,
            planned_seconds=5 * 60,
            id=interval_id,
            position=1,
            started_at=LATER,
            actual_seconds=None,
            ended_at=None,
            status=None,
        )
    ]


# --- finish_interval ---------------------------------------------------------


def test_a_finished_interval_gets_its_status_actual_time_and_end(
    session_repository, work_category_id
):
    session_id = session_repository.create_flow(STARTED)
    interval_id = session_repository.start_interval(
        session_id, 1, work_interval(work_category_id)
    )

    session_repository.finish_interval(
        interval_id,
        status=IntervalStatus.COMPLETED,
        actual_seconds=25 * 60,
        ended_at=LATER,
    )

    assert session_repository.list_intervals(session_id) == [
        IntervalEntity(
            kind=IntervalKind.WORK,
            category_id=work_category_id,
            planned_seconds=25 * 60,
            id=interval_id,
            position=1,
            started_at=STARTED,
            actual_seconds=25 * 60,
            ended_at=LATER,
            status=IntervalStatus.COMPLETED,
        )
    ]


@pytest.mark.parametrize("status", list(IntervalStatus))
def test_every_interval_status_can_be_written_and_read_back(
    session_repository, work_category_id, status
):
    session_id = session_repository.create_flow(STARTED)
    interval_id = session_repository.start_interval(
        session_id, 1, work_interval(work_category_id)
    )

    session_repository.finish_interval(
        interval_id, status=status, actual_seconds=600, ended_at=LATER
    )

    assert session_repository.list_intervals(session_id)[0].status == status


def test_finishing_an_interval_leaves_the_others_untouched(
    session_repository, work_category_id
):
    session_id = session_repository.create_flow(STARTED)
    first_id = session_repository.start_interval(
        session_id, 1, work_interval(work_category_id)
    )
    session_repository.start_interval(session_id, 2, short_break())

    session_repository.finish_interval(
        first_id, status=IntervalStatus.COMPLETED, actual_seconds=25 * 60, ended_at=LATER
    )

    first, second = session_repository.list_intervals(session_id)
    assert first.status == IntervalStatus.COMPLETED
    assert (second.status, second.actual_seconds, second.ended_at) == (None, None, None)


def test_finishing_an_unknown_interval_raises_lookup_error(session_repository):
    with pytest.raises(LookupError):
        session_repository.finish_interval(
            999, status=IntervalStatus.COMPLETED, actual_seconds=1, ended_at=LATER
        )


# --- finish_session ----------------------------------------------------------


def test_a_finished_session_gets_its_status_and_end(db, session_repository):
    session_id = session_repository.create_flow(STARTED)

    session_repository.finish_session(
        session_id, status=SessionStatus.COMPLETED, ended_at=LATER
    )

    session = stored_session(db, session_id)
    assert session["status"] == "completed"
    assert session["ended_at"] == "2026-01-01T12:25:00Z"
    assert session["started_at"] == "2026-01-01T12:00:00Z"


@pytest.mark.parametrize("status", [SessionStatus.COMPLETED, SessionStatus.STOPPED])
def test_a_session_can_end_as_completed_or_stopped(db, session_repository, status):
    session_id = session_repository.create_flow(STARTED)

    session_repository.finish_session(session_id, status=status, ended_at=LATER)

    assert stored_session(db, session_id)["status"] == status


def test_finishing_a_session_leaves_the_others_running(db, session_repository):
    first = session_repository.create_flow(STARTED)
    second = session_repository.create_flow(LATER)

    session_repository.finish_session(
        first, status=SessionStatus.STOPPED, ended_at=LATER
    )

    assert stored_session(db, second)["status"] == "running"


def test_finishing_an_unknown_session_raises_lookup_error(session_repository):
    with pytest.raises(LookupError):
        session_repository.finish_session(
            999, status=SessionStatus.STOPPED, ended_at=LATER
        )


# --- list_intervals ----------------------------------------------------------


def test_intervals_are_listed_in_the_order_of_their_positions(
    session_repository, work_category_id
):
    session_id = session_repository.create_flow(STARTED)
    session_repository.start_interval(session_id, 2, short_break())
    session_repository.start_interval(session_id, 3, work_interval(work_category_id))
    session_repository.start_interval(session_id, 1, work_interval(work_category_id))

    positions = [
        interval.position for interval in session_repository.list_intervals(session_id)
    ]

    assert positions == [1, 2, 3]


def test_only_the_intervals_of_the_given_session_are_listed(session_repository):
    first = session_repository.create_flow(STARTED)
    second = session_repository.create_flow(LATER)
    session_repository.start_interval(first, 1, short_break())
    session_repository.start_interval(second, 1, short_break())
    session_repository.start_interval(second, 2, short_break())

    assert len(session_repository.list_intervals(first)) == 1
    assert len(session_repository.list_intervals(second)) == 2


def test_a_session_without_intervals_has_an_empty_list(session_repository):
    session_id = session_repository.create_flow(STARTED)

    assert session_repository.list_intervals(session_id) == []


def test_times_are_read_back_as_utc_datetimes(session_repository):
    session_id = session_repository.create_flow(STARTED)
    session_repository.start_interval(session_id, 1, short_break(started_at=LATER))

    started_at = session_repository.list_intervals(session_id)[0].started_at

    assert started_at == LATER
    assert started_at.utcoffset() == timedelta(0)


# --- last_flow_category_id ---------------------------------------------------


def test_there_is_no_last_category_before_any_flow(session_repository):
    assert session_repository.last_flow_category_id() is None


def test_the_last_category_is_the_one_of_the_flows_work_intervals(
    session_repository, work_category_id
):
    session_id = session_repository.create_flow(STARTED)
    session_repository.start_interval(session_id, 1, work_interval(work_category_id))
    session_repository.start_interval(session_id, 2, short_break())

    assert session_repository.last_flow_category_id() == work_category_id


def test_the_most_recent_flow_decides(
    session_repository, work_category_id, reading_category_id
):
    earlier = session_repository.create_flow(STARTED)
    session_repository.start_interval(earlier, 1, work_interval(work_category_id))
    later = session_repository.create_flow(LATER)
    session_repository.start_interval(
        later, 1, work_interval(reading_category_id, started_at=LATER)
    )

    assert session_repository.last_flow_category_id() == reading_category_id


def test_scenario_sessions_are_ignored(
    db, session_repository, work_category_id, reading_category_id
):
    flow_id = session_repository.create_flow(STARTED)
    session_repository.start_interval(flow_id, 1, work_interval(work_category_id))
    scenario_id = db.insert(
        "INSERT INTO session (kind, status, started_at, scenario_name, scenario_snapshot)"
        " VALUES ('scenario', 'completed', :started_at, 'Day', '{}')",
        {"started_at": "2026-01-01T13:00:00Z"},
    )
    session_repository.start_interval(
        scenario_id, 1, work_interval(reading_category_id, started_at=LATER)
    )

    assert session_repository.last_flow_category_id() == work_category_id


def test_there_is_no_last_category_when_only_scenarios_were_run(
    db, session_repository, work_category_id
):
    scenario_id = db.insert(
        "INSERT INTO session (kind, status, started_at, scenario_name, scenario_snapshot)"
        " VALUES ('scenario', 'completed', :started_at, 'Day', '{}')",
        {"started_at": "2026-01-01T13:00:00Z"},
    )
    session_repository.start_interval(scenario_id, 1, work_interval(work_category_id))

    assert session_repository.last_flow_category_id() is None


# --- interrupt_running_sessions ----------------------------------------------


def all_rows(db):
    sessions = db.query("SELECT * FROM session ORDER BY id", mapper=dict)
    intervals = db.query("SELECT * FROM interval ORDER BY id", mapper=dict)
    return sessions, intervals


def add_running_flow(session_repository, category_id, started_at=STARTED):
    """A flow with one running work interval, as an app closed in the middle leaves it."""
    session_id = session_repository.create_flow(started_at)
    interval_id = session_repository.start_interval(
        session_id, 1, work_interval(category_id, started_at=started_at)
    )
    return session_id, interval_id


def test_a_running_session_becomes_interrupted(
    db, session_repository, work_category_id
):
    session_id, _ = add_running_flow(session_repository, work_category_id)

    session_repository.interrupt_running_sessions()

    session = stored_session(db, session_id)
    assert session["status"] == "interrupted"
    assert session["ended_at"] is None


def test_its_unfinished_interval_becomes_interrupted_without_an_actual_duration(
    session_repository, work_category_id
):
    session_id, _ = add_running_flow(session_repository, work_category_id)

    session_repository.interrupt_running_sessions()

    (interval,) = session_repository.list_intervals(session_id)
    assert interval.status == IntervalStatus.INTERRUPTED
    assert interval.actual_seconds is None
    assert interval.ended_at is None
    assert interval.started_at == STARTED


def test_the_finished_intervals_of_the_session_are_left_as_they_were(
    session_repository, work_category_id
):
    session_id, first_id = add_running_flow(session_repository, work_category_id)
    session_repository.finish_interval(
        first_id, status=IntervalStatus.COMPLETED, actual_seconds=25 * 60, ended_at=LATER
    )
    session_repository.start_interval(session_id, 2, short_break())
    completed_before = session_repository.list_intervals(session_id)[0]

    session_repository.interrupt_running_sessions()

    completed, interrupted = session_repository.list_intervals(session_id)
    assert completed == completed_before
    assert interrupted.status == IntervalStatus.INTERRUPTED


def test_a_session_interrupted_while_waiting_has_no_interval_to_change(
    db, session_repository, work_category_id
):
    session_id, interval_id = add_running_flow(session_repository, work_category_id)
    session_repository.finish_interval(
        interval_id,
        status=IntervalStatus.COMPLETED,
        actual_seconds=25 * 60,
        ended_at=LATER,
    )
    intervals_before = session_repository.list_intervals(session_id)

    session_repository.interrupt_running_sessions()

    assert stored_session(db, session_id)["status"] == "interrupted"
    assert session_repository.list_intervals(session_id) == intervals_before


def test_every_running_session_is_interrupted(db, session_repository, work_category_id):
    first_id, _ = add_running_flow(session_repository, work_category_id)
    second_id, _ = add_running_flow(
        session_repository, work_category_id, started_at=LATER
    )

    session_repository.interrupt_running_sessions()

    assert stored_session(db, first_id)["status"] == "interrupted"
    assert stored_session(db, second_id)["status"] == "interrupted"


def test_a_running_scenario_session_is_interrupted_too(
    db, session_repository, work_category_id
):
    session_id = db.insert(
        "INSERT INTO session (kind, status, started_at, scenario_name, scenario_snapshot)"
        " VALUES ('scenario', 'running', :started_at, 'Day', '{}')",
        {"started_at": "2026-01-01T12:00:00Z"},
    )
    session_repository.start_interval(session_id, 1, work_interval(work_category_id))

    session_repository.interrupt_running_sessions()

    assert stored_session(db, session_id)["status"] == "interrupted"
    assert session_repository.list_intervals(session_id)[0].status == (
        IntervalStatus.INTERRUPTED
    )


@pytest.mark.parametrize("status", [SessionStatus.COMPLETED, SessionStatus.STOPPED])
def test_finished_sessions_and_their_intervals_are_not_touched(
    db, session_repository, work_category_id, status
):
    session_id, interval_id = add_running_flow(session_repository, work_category_id)
    session_repository.finish_interval(
        interval_id, status=IntervalStatus.STOPPED, actual_seconds=600, ended_at=LATER
    )
    session_repository.finish_session(session_id, status=status, ended_at=LATER)
    rows_before = all_rows(db)

    session_repository.interrupt_running_sessions()

    assert all_rows(db) == rows_before


def test_running_it_again_changes_nothing(db, session_repository, work_category_id):
    add_running_flow(session_repository, work_category_id)
    session_repository.interrupt_running_sessions()
    rows_after_the_first_run = all_rows(db)

    session_repository.interrupt_running_sessions()

    assert all_rows(db) == rows_after_the_first_run


def test_a_clean_database_stays_as_it_is(db, session_repository):
    rows_before = all_rows(db)

    session_repository.interrupt_running_sessions()

    assert all_rows(db) == rows_before == ([], [])


# --- scenario sessions -------------------------------------------------------------


def test_a_scenario_session_keeps_its_name_and_snapshot(db, session_repository, work_category_id):
    scenario = Scenario("Work day", (ScenarioRow(work_category_id, 2),), repeat_count=3)

    session_id = session_repository.create_scenario_session(STARTED, scenario)

    session = db.query_one(
        "SELECT * FROM session WHERE id = ?", (session_id,), mapper=dict
    )
    assert (session["kind"], session["status"]) == ("scenario", "running")
    assert session["started_at"] == "2026-01-01T12:00:00Z"
    assert session["scenario_name"] == "Work day"
    assert from_snapshot(session["scenario_snapshot"]) == scenario


# --- interrupted scenario sessions -------------------------------------------------


def interrupted_scenario_session(db, session_repository, work_category_id, scenario):
    session_id = session_repository.create_scenario_session(STARTED, scenario)
    session_repository.start_interval(session_id, 1, work_interval(work_category_id))
    session_repository.interrupt_running_sessions()
    return session_id


@pytest.fixture
def scenario(work_category_id):
    return Scenario("Day", (ScenarioRow(work_category_id, 2),))


def test_there_is_no_interrupted_scenario_session_in_a_clean_database(session_repository):
    assert session_repository.latest_interrupted_scenario_session() is None


def test_an_interrupted_scenario_session_comes_with_its_scenario_and_intervals(
    db, session_repository, work_category_id, scenario
):
    session_id = interrupted_scenario_session(db, session_repository, work_category_id, scenario)

    interrupted = session_repository.latest_interrupted_scenario_session()

    assert interrupted.session_id == session_id
    assert interrupted.scenario == scenario
    assert [(i.position, i.status) for i in interrupted.intervals] == [
        (1, IntervalStatus.INTERRUPTED)
    ]


def test_a_flow_is_not_an_interrupted_scenario_session(db, session_repository, work_category_id):
    session_repository.create_flow(STARTED)
    session_repository.interrupt_running_sessions()

    assert session_repository.latest_interrupted_scenario_session() is None


def test_a_newer_session_hides_an_older_interrupted_one(
    db, session_repository, work_category_id, scenario
):
    interrupted_scenario_session(db, session_repository, work_category_id, scenario)
    newer = session_repository.create_flow(LATER)
    session_repository.finish_session(newer, status=SessionStatus.STOPPED, ended_at=LATER)

    assert session_repository.latest_interrupted_scenario_session() is None


def test_reopening_makes_the_session_run_again(
    db, session_repository, work_category_id, scenario
):
    session_id = interrupted_scenario_session(db, session_repository, work_category_id, scenario)

    session_repository.reopen_session(session_id)

    row = db.query_one("SELECT status, ended_at FROM session", mapper=dict)
    assert row == {"status": "running", "ended_at": None}


def test_stopping_an_interrupted_session_leaves_its_end_unknown(
    db, session_repository, work_category_id, scenario
):
    session_id = interrupted_scenario_session(db, session_repository, work_category_id, scenario)

    session_repository.stop_interrupted_session(session_id)

    row = db.query_one("SELECT status, ended_at FROM session", mapper=dict)
    assert row == {"status": "stopped", "ended_at": None}
    assert session_repository.latest_interrupted_scenario_session() is None

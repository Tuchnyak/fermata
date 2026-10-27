import sqlite3
from datetime import timedelta

import pytest
from timer.engine import Engine
from timer.intervals import IntervalKind, IntervalStatus
from timer.recorder import Recorder
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.sessions import SessionRepository
from timer.storage.settings import SettingsRepository


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def settings_repository(db):
    return SettingsRepository(db)


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def work_category_id(db):
    return CategoryRepository(db).create("Work", "#112233").id


@pytest.fixture
def engine(db, settings_repository, session_repository, clock):
    recorder = Recorder(db, session_repository)
    return Engine(
        get_settings=settings_repository.get_all,
        clock=clock,
        on_flow_event=recorder.record,
    )


@pytest.fixture
def auto_engine(engine, settings_repository):
    settings_repository.set("transition_mode", "auto")
    return engine


def run_to_the_end(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


def stored_sessions(db):
    return db.query("SELECT * FROM session ORDER BY id", mapper=dict)


def only_session_id(db):
    (session,) = stored_sessions(db)
    return session["id"]


def summary(interval):
    return (
        interval.position,
        interval.kind,
        interval.category_id,
        interval.planned_seconds,
        interval.actual_seconds,
        interval.started_at,
        interval.ended_at,
        interval.status,
    )


# --- a whole flow ----------------------------------------------------------------


def test_a_flow_is_written_with_correct_statuses_positions_and_durations(
    db, auto_engine, session_repository, work_category_id, clock
):
    t0 = clock()
    auto_engine.start_flow(work_category_id)
    run_to_the_end(auto_engine, clock)  # the work interval is completed; a break starts
    run_to_the_end(auto_engine, clock)  # the break is completed; a work interval starts
    clock.advance(600)
    auto_engine.skip()  # the work interval is skipped; a break starts
    clock.advance(120)
    auto_engine.stop()  # the break is stopped

    session = stored_sessions(db)[0]
    assert (session["kind"], session["status"]) == ("flow", "stopped")
    assert session["started_at"] == "2026-01-01T12:00:00Z"
    assert session["ended_at"] == "2026-01-01T12:42:00Z"

    def minutes(count):
        return t0 + timedelta(minutes=count)

    assert [
        summary(interval)
        for interval in session_repository.list_intervals(session["id"])
    ] == [
        (1, IntervalKind.WORK, work_category_id, 1500, 1500, minutes(0), minutes(25),
         IntervalStatus.COMPLETED),
        (2, IntervalKind.SHORT_BREAK, None, 300, 300, minutes(25), minutes(30),
         IntervalStatus.COMPLETED),
        (3, IntervalKind.WORK, work_category_id, 1500, 600, minutes(30), minutes(40),
         IntervalStatus.SKIPPED),
        (4, IntervalKind.SHORT_BREAK, None, 300, 120, minutes(40), minutes(42),
         IntervalStatus.STOPPED),
    ]  # fmt: skip


# --- step by step ----------------------------------------------------------------


def test_starting_a_flow_writes_a_running_session_with_its_running_first_interval(
    db, engine, session_repository, work_category_id
):
    engine.start_flow(work_category_id)

    session = stored_sessions(db)[0]
    assert (session["status"], session["ended_at"]) == ("running", None)
    (interval,) = session_repository.list_intervals(session["id"])
    assert (interval.position, interval.kind, interval.status) == (
        1,
        IntervalKind.WORK,
        None,
    )
    assert interval.category_id == work_category_id


def test_completion_in_confirm_mode_finishes_the_interval_and_starts_nothing(
    db, engine, session_repository, work_category_id, clock
):
    engine.start_flow(work_category_id)

    run_to_the_end(engine, clock)

    (interval,) = session_repository.list_intervals(only_session_id(db))
    assert (interval.status, interval.actual_seconds) == (IntervalStatus.COMPLETED, 1500)
    assert stored_sessions(db)[0]["status"] == "running"


def test_confirm_writes_the_next_interval_at_the_next_position(
    db, engine, session_repository, work_category_id, clock
):
    engine.start_flow(work_category_id)
    run_to_the_end(engine, clock)

    engine.confirm()

    intervals = session_repository.list_intervals(only_session_id(db))
    assert [(interval.position, interval.kind) for interval in intervals] == [
        (1, IntervalKind.WORK),
        (2, IntervalKind.SHORT_BREAK),
    ]
    assert intervals[1].status is None


def test_skip_finishes_the_interval_and_writes_the_next_one(
    db, engine, session_repository, work_category_id, clock
):
    engine.start_flow(work_category_id)
    clock.advance(600)

    engine.skip()

    first, second = session_repository.list_intervals(only_session_id(db))
    assert (first.status, first.actual_seconds) == (IntervalStatus.SKIPPED, 600)
    assert (second.position, second.kind, second.status) == (
        2,
        IntervalKind.SHORT_BREAK,
        None,
    )


def test_stop_while_waiting_ends_the_session_without_a_new_interval(
    db, engine, session_repository, work_category_id, clock
):
    engine.start_flow(work_category_id)
    run_to_the_end(engine, clock)
    clock.advance(60)

    engine.stop()

    session = stored_sessions(db)[0]
    assert session["status"] == "stopped"
    assert session["ended_at"] == "2026-01-01T12:26:00Z"
    assert len(session_repository.list_intervals(session["id"])) == 1


# --- several flows ---------------------------------------------------------------


def test_every_flow_gets_its_own_session_and_numbers_its_intervals_from_one(
    db, engine, session_repository, work_category_id
):
    engine.start_flow(work_category_id)
    engine.skip()
    engine.stop()
    engine.start_flow(work_category_id)

    first, second = stored_sessions(db)

    assert [i.position for i in session_repository.list_intervals(first["id"])] == [1, 2]
    assert [i.position for i in session_repository.list_intervals(second["id"])] == [1]
    assert (first["status"], second["status"]) == ("stopped", "running")


def test_the_recorded_flow_provides_the_category_for_the_next_one(
    engine, session_repository, work_category_id
):
    engine.start_flow(work_category_id)
    engine.stop()

    assert session_repository.last_flow_category_id() == work_category_id


# --- each step in one transaction --------------------------------------------------


def test_a_step_that_fails_leaves_nothing_behind(db, engine):
    unknown_category_id = 999

    with pytest.raises(sqlite3.IntegrityError):
        engine.start_flow(unknown_category_id)

    assert stored_sessions(db) == []

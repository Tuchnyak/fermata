import pytest
from fermata.engine import Engine
from fermata.intervals import IntervalKind, IntervalStatus
from fermata.recorder import Recorder
from fermata.scenarios import Scenario, ScenarioRow, to_snapshot
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.sessions import SessionRepository
from fermata.storage.settings import SettingsRepository


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def example(db):
    categories = CategoryRepository(db)
    work = categories.create("Work", "#112233")
    personal = categories.create("Personal", "#445566")
    return Scenario(
        name="Work day",
        rows=(ScenarioRow(work.id, 2), ScenarioRow(personal.id, 1)),
        repeat_count=2,
    )


@pytest.fixture
def engine(db, session_repository, clock):
    SettingsRepository(db).set("transition_mode", "auto")
    recorder = Recorder(db, session_repository)
    return Engine(
        get_settings=SettingsRepository(db).get_all,
        clock=clock,
        on_flow_event=recorder.record,
    )


def run_to_the_end(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


def stored_sessions(db):
    return db.query("SELECT * FROM session ORDER BY id", mapper=dict)


def test_starting_a_scenario_writes_a_running_scenario_session_with_its_snapshot(
    db, engine, example, session_repository
):
    engine.start_scenario(example)

    (session,) = stored_sessions(db)
    assert (session["kind"], session["status"]) == ("scenario", "running")
    assert session["scenario_name"] == "Work day"
    assert session["scenario_snapshot"] == to_snapshot(example)
    (interval,) = session_repository.list_intervals(session["id"])
    assert (interval.position, interval.kind, interval.status) == (
        1,
        IntervalKind.WORK,
        None,
    )


def test_a_scenario_that_ran_to_its_end_is_written_as_completed(
    db, engine, example, session_repository, clock
):
    engine.start_scenario(example)
    for _ in range(11):  # six work intervals and the five breaks between them
        run_to_the_end(engine, clock)

    (session,) = stored_sessions(db)
    assert session["status"] == "completed"
    intervals = session_repository.list_intervals(session["id"])
    assert [i.position for i in intervals] == list(range(1, 12))
    assert {i.status for i in intervals} == {IntervalStatus.COMPLETED}
    assert session["ended_at"] == "2026-01-01T15:05:00Z"  # 185 minutes after the start


def test_skipping_the_last_work_interval_writes_the_session_as_completed(
    db, engine, example, session_repository, clock
):
    engine.start_scenario(example)
    for _ in range(10):
        run_to_the_end(engine, clock)
    clock.advance(600)

    engine.skip()

    (session,) = stored_sessions(db)
    assert session["status"] == "completed"
    last = session_repository.list_intervals(session["id"])[-1]
    assert (last.status, last.actual_seconds) == (IntervalStatus.SKIPPED, 600)


def test_stopping_a_scenario_writes_the_session_as_stopped(db, engine, example, clock):
    engine.start_scenario(example)
    clock.advance(60)

    engine.stop()

    (session,) = stored_sessions(db)
    assert session["status"] == "stopped"


def test_a_scenario_does_not_count_as_the_previous_flow(
    db, engine, example, session_repository, clock
):
    engine.start_scenario(example)
    engine.stop()

    assert session_repository.last_flow_category_id() is None

from datetime import timedelta

import pytest
from timer.engine import Engine
from timer.intervals import (
    FinishedInterval,
    IntervalKind,
    IntervalStatus,
    RunningInterval,
)
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.settings import SettingsRepository

CATEGORY_ID = 7  # the engine only carries the id; it does not look the category up


@pytest.fixture
def settings_repository():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return SettingsRepository(db)


@pytest.fixture
def engine(settings_repository, clock):
    return Engine(get_settings=settings_repository.get_all, clock=clock)


# --- idle --------------------------------------------------------------------


def test_a_new_engine_is_idle(engine):
    assert engine.current_interval is None
    assert engine.finished_intervals == []


def test_tick_while_idle_changes_nothing(engine, clock):
    clock.advance(100)

    engine.tick()

    assert engine.current_interval is None
    assert engine.finished_intervals == []


# --- starting a flow ---------------------------------------------------------


def test_starting_a_flow_begins_a_work_interval_of_the_default_length(engine, clock):
    engine.start_flow(CATEGORY_ID)

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=CATEGORY_ID,
        planned_seconds=25 * 60,
        started_at=clock(),
    )


def test_the_length_comes_from_the_settings(engine, settings_repository):
    settings_repository.set("work_minutes", 40)

    engine.start_flow(CATEGORY_ID)

    assert engine.current_interval.planned_seconds == 40 * 60


# --- remaining time ----------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "remaining"),
    [(0, 1500), (1, 1499), (0.5, 1499.5), (90, 1410), (600, 900), (1499, 1)],
)
def test_remaining_time_is_computed_from_the_clock_without_any_ticks(
    engine, clock, elapsed, remaining
):
    engine.start_flow(CATEGORY_ID)

    clock.advance(elapsed)

    assert engine.remaining_seconds() == remaining


# --- completion --------------------------------------------------------------


def test_the_interval_is_still_running_before_its_time_has_elapsed(engine, clock):
    engine.start_flow(CATEGORY_ID)

    clock.advance(25 * 60 - 1)
    engine.tick()

    assert engine.current_interval is not None
    assert engine.finished_intervals == []


def test_the_interval_completes_when_its_time_has_elapsed(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()

    clock.advance(25 * 60)
    engine.tick()

    assert engine.current_interval is None
    assert engine.finished_intervals == [
        FinishedInterval(
            kind=IntervalKind.WORK,
            category_id=CATEGORY_ID,
            planned_seconds=25 * 60,
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=25),
            actual_seconds=25 * 60,
            status=IntervalStatus.COMPLETED,
        )
    ]


def test_a_late_tick_still_records_the_planned_time_as_actual(engine, clock):
    engine.start_flow(CATEGORY_ID)

    clock.advance(25 * 60 + 300)
    engine.tick()

    assert engine.finished_intervals[0].actual_seconds == 25 * 60


def test_a_late_tick_records_the_calculated_end_not_the_time_of_the_tick(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()

    clock.advance(25 * 60 + 300)
    engine.tick()

    assert engine.finished_intervals[0].ended_at == started_at + timedelta(minutes=25)


def test_the_number_and_spacing_of_ticks_do_not_change_when_the_interval_ends(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)

    for seconds in [7, 600, 892]:  # 1499 seconds in total
        clock.advance(seconds)
        engine.tick()
    assert engine.finished_intervals == []

    clock.advance(1)
    engine.tick()
    assert len(engine.finished_intervals) == 1


# --- pause and resume --------------------------------------------------------


def test_a_running_interval_is_not_paused(engine):
    engine.start_flow(CATEGORY_ID)

    assert engine.is_paused is False


def test_pause_marks_the_interval_as_paused_and_resume_clears_the_mark(engine):
    engine.start_flow(CATEGORY_ID)

    engine.pause()
    assert engine.is_paused is True

    engine.resume()
    assert engine.is_paused is False


def test_the_remaining_time_does_not_change_while_paused(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)

    engine.pause()
    clock.advance(1000)

    assert engine.remaining_seconds() == 25 * 60 - 600


def test_a_paused_interval_does_not_finish_however_long_the_pause_lasts(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(60)

    engine.pause()
    clock.advance(10 * 3600)
    engine.tick()

    assert engine.current_interval is not None
    assert engine.finished_intervals == []


def test_resume_continues_the_countdown_from_where_it_stopped(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)
    engine.pause()
    clock.advance(1000)

    engine.resume()
    clock.advance(100)

    assert engine.remaining_seconds() == 25 * 60 - 700


def test_several_pauses_add_up(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(300)
    engine.pause()
    clock.advance(1000)
    engine.resume()
    clock.advance(300)
    engine.pause()
    clock.advance(2000)
    engine.resume()
    clock.advance(100)

    assert engine.remaining_seconds() == 25 * 60 - 700


def test_paused_time_is_not_counted_as_worked_time(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)
    engine.pause()
    clock.advance(30 * 60)
    engine.resume()
    clock.advance(900)  # 600 + 900 seconds worked: the whole interval

    engine.tick()

    assert engine.finished_intervals == [
        FinishedInterval(
            kind=IntervalKind.WORK,
            category_id=CATEGORY_ID,
            planned_seconds=25 * 60,
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=25 + 30),
            actual_seconds=25 * 60,
            status=IntervalStatus.COMPLETED,
        )
    ]


def test_pausing_a_paused_interval_has_no_effect(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)
    engine.pause()
    clock.advance(100)

    engine.pause()  # must not restart the pause
    clock.advance(100)
    engine.resume()
    clock.advance(900)
    engine.tick()

    assert engine.finished_intervals[0].ended_at == started_at + timedelta(
        seconds=25 * 60 + 200
    )


def test_resuming_a_running_interval_has_no_effect(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)

    engine.resume()
    clock.advance(100)

    assert engine.remaining_seconds() == 25 * 60 - 700


def test_pause_and_resume_while_idle_do_nothing(engine):
    engine.pause()
    engine.resume()

    assert engine.is_paused is False
    assert engine.current_interval is None


def test_a_clock_set_back_during_a_pause_does_not_change_the_worked_time(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)
    engine.pause()

    clock.advance(-100)
    engine.resume()

    assert engine.remaining_seconds() == 25 * 60 - 600


# --- settings are read at the start ------------------------------------------


def test_a_settings_change_does_not_affect_the_running_interval(
    engine, clock, settings_repository
):
    engine.start_flow(CATEGORY_ID)

    settings_repository.set("work_minutes", 40)

    assert engine.current_interval.planned_seconds == 25 * 60
    clock.advance(25 * 60)
    engine.tick()
    assert engine.finished_intervals[0].planned_seconds == 25 * 60

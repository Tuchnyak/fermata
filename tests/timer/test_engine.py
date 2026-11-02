from datetime import timedelta

import pytest
from timer.engine import Engine, FlowEvent
from timer.intervals import (
    BaseInterval,
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
def events():
    return []


@pytest.fixture
def engine(settings_repository, clock, events):
    return Engine(
        get_settings=settings_repository.get_all,
        clock=clock,
        on_flow_event=events.append,
    )


def run_to_the_end(engine, clock):
    """Let the running interval's time elapse and let the engine notice it."""
    clock.advance(engine.remaining_seconds())
    engine.tick()


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


# --- skip --------------------------------------------------------------------


def test_skipping_a_work_interval_starts_a_short_break_immediately(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)

    engine.skip()

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=clock(),
    )
    assert engine.remaining_seconds() == 5 * 60


def test_a_skipped_work_interval_is_recorded_with_the_time_actually_worked(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)

    engine.skip()

    assert engine.finished_intervals == [
        FinishedInterval(
            kind=IntervalKind.WORK,
            category_id=CATEGORY_ID,
            planned_seconds=25 * 60,
            started_at=started_at,
            ended_at=started_at + timedelta(seconds=600),
            actual_seconds=600,
            status=IntervalStatus.SKIPPED,
        )
    ]


def test_time_spent_paused_is_not_counted_in_a_skipped_interval(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(300)
    engine.pause()
    clock.advance(1000)
    engine.resume()
    clock.advance(300)

    engine.skip()

    skipped = engine.finished_intervals[0]
    assert skipped.actual_seconds == 600
    assert skipped.ended_at == started_at + timedelta(seconds=1600)


def test_a_paused_interval_can_be_skipped(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)
    engine.pause()
    clock.advance(1000)

    engine.skip()

    skipped = engine.finished_intervals[0]
    assert skipped.actual_seconds == 600
    assert skipped.ended_at == started_at + timedelta(seconds=1600)
    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK
    assert engine.is_paused is False


@pytest.mark.parametrize(
    ("elapsed", "actual_seconds"), [(0, 0), (0.9, 0), (90.9, 90), (600, 600)]
)
def test_the_worked_time_of_a_skipped_interval_is_in_whole_seconds_rounded_down(
    engine, clock, elapsed, actual_seconds
):
    engine.start_flow(CATEGORY_ID)
    clock.advance(elapsed)

    engine.skip()

    assert engine.finished_intervals[0].actual_seconds == actual_seconds


def test_the_worked_time_of_a_skipped_interval_never_exceeds_the_planned_time(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)

    clock.advance(25 * 60 + 300)  # the time is up, but no tick has noticed it yet
    engine.skip()

    assert engine.finished_intervals[0].actual_seconds == 25 * 60


def test_skipping_a_break_starts_a_work_interval_of_the_same_category(engine, clock):
    engine.start_flow(CATEGORY_ID)
    engine.skip()  # the work interval; a short break starts
    clock.advance(120)

    engine.skip()

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=CATEGORY_ID,
        planned_seconds=25 * 60,
        started_at=clock(),
    )


def test_a_skipped_break_is_recorded_with_the_time_actually_taken(engine, clock):
    engine.start_flow(CATEGORY_ID)
    engine.skip()
    break_started_at = clock()
    clock.advance(120)

    engine.skip()

    assert engine.finished_intervals[1] == FinishedInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=break_started_at,
        ended_at=break_started_at + timedelta(seconds=120),
        actual_seconds=120,
        status=IntervalStatus.SKIPPED,
    )


def test_skipped_work_intervals_count_toward_the_long_break(engine):
    engine.start_flow(CATEGORY_ID)
    for _ in range(3):
        engine.skip()  # a work interval
        engine.skip()  # the short break after it

    engine.skip()  # the fourth work interval

    assert engine.current_interval.kind == IntervalKind.LONG_BREAK
    assert engine.current_interval.planned_seconds == 15 * 60


def test_a_work_interval_follows_a_skipped_long_break(engine):
    engine.start_flow(CATEGORY_ID)
    for _ in range(7):
        engine.skip()  # four work intervals and three short breaks

    engine.skip()  # the long break

    assert engine.current_interval.kind == IntervalKind.WORK


def test_the_next_interval_takes_its_length_from_the_settings_at_the_time_it_starts(
    engine, settings_repository
):
    engine.start_flow(CATEGORY_ID)
    settings_repository.set("short_break_minutes", 10)

    engine.skip()
    assert engine.current_interval.planned_seconds == 10 * 60

    settings_repository.set("work_minutes", 40)
    engine.skip()
    assert engine.current_interval.planned_seconds == 40 * 60


@pytest.mark.parametrize("transition_mode", ["auto", "confirm", "mixed"])
def test_skip_starts_the_next_interval_immediately_in_every_transition_mode(
    engine, settings_repository, transition_mode
):
    settings_repository.set("transition_mode", transition_mode)
    engine.start_flow(CATEGORY_ID)

    engine.skip()
    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK

    engine.skip()
    assert engine.current_interval.kind == IntervalKind.WORK


def test_skip_while_idle_does_nothing(engine):
    engine.skip()

    assert engine.current_interval is None
    assert engine.finished_intervals == []


# --- stop --------------------------------------------------------------------


def test_stop_records_the_interval_as_stopped_with_the_time_actually_worked(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)

    engine.stop()

    assert engine.finished_intervals == [
        FinishedInterval(
            kind=IntervalKind.WORK,
            category_id=CATEGORY_ID,
            planned_seconds=25 * 60,
            started_at=started_at,
            ended_at=started_at + timedelta(seconds=600),
            actual_seconds=600,
            status=IntervalStatus.STOPPED,
        )
    ]


def test_stop_ends_the_flow_and_the_engine_becomes_idle(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)

    engine.stop()
    clock.advance(10 * 60)
    engine.tick()

    assert engine.current_interval is None
    assert engine.is_paused is False
    assert engine.remaining_seconds() == 0
    assert len(engine.finished_intervals) == 1


def test_a_break_can_be_stopped(engine, clock):
    engine.start_flow(CATEGORY_ID)
    engine.skip()
    break_started_at = clock()
    clock.advance(120)

    engine.stop()

    assert engine.finished_intervals[1] == FinishedInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=break_started_at,
        ended_at=break_started_at + timedelta(seconds=120),
        actual_seconds=120,
        status=IntervalStatus.STOPPED,
    )
    assert engine.current_interval is None


def test_time_spent_paused_is_not_counted_in_a_stopped_interval(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(300)
    engine.pause()
    clock.advance(1000)
    engine.resume()
    clock.advance(300)

    engine.stop()

    stopped = engine.finished_intervals[0]
    assert stopped.actual_seconds == 600
    assert stopped.ended_at == started_at + timedelta(seconds=1600)


def test_a_paused_interval_can_be_stopped(engine, clock):
    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(600)
    engine.pause()
    clock.advance(1000)

    engine.stop()

    stopped = engine.finished_intervals[0]
    assert stopped.actual_seconds == 600
    assert stopped.ended_at == started_at + timedelta(seconds=1600)
    assert engine.is_paused is False


def test_the_worked_time_of_a_stopped_interval_is_in_whole_seconds_rounded_down(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)
    clock.advance(90.9)

    engine.stop()

    assert engine.finished_intervals[0].actual_seconds == 90


def test_the_worked_time_of_a_stopped_interval_never_exceeds_the_planned_time(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)

    clock.advance(25 * 60 + 300)  # the time is up, but no tick has noticed it yet
    engine.stop()

    assert engine.finished_intervals[0].actual_seconds == 25 * 60


def test_stop_while_idle_does_nothing(engine):
    engine.stop()

    assert engine.current_interval is None
    assert engine.finished_intervals == []


def test_stopping_twice_records_the_interval_once(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)

    engine.stop()
    engine.stop()

    assert len(engine.finished_intervals) == 1


# --- a new flow after a stop ---------------------------------------------------


def test_a_new_flow_begins_with_a_work_interval_of_its_own_category(engine, clock):
    engine.start_flow(CATEGORY_ID)
    engine.stop()
    clock.advance(3600)

    engine.start_flow(CATEGORY_ID + 1)

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=CATEGORY_ID + 1,
        planned_seconds=25 * 60,
        started_at=clock(),
    )


def test_the_breaks_of_a_new_flow_lead_back_to_its_own_category(engine):
    engine.start_flow(CATEGORY_ID)
    engine.stop()

    engine.start_flow(CATEGORY_ID + 1)
    engine.skip()  # the work interval; a short break starts
    engine.skip()  # the break; a work interval starts

    assert engine.current_interval.category_id == CATEGORY_ID + 1


def test_a_new_flow_starts_with_no_finished_intervals(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)
    engine.stop()

    engine.start_flow(CATEGORY_ID)

    assert engine.finished_intervals == []


def test_a_new_flow_counts_work_intervals_toward_the_long_break_from_zero(engine):
    engine.start_flow(CATEGORY_ID)
    for _ in range(5):
        engine.skip()  # three work intervals and two short breaks
    engine.stop()  # the third short break

    engine.start_flow(CATEGORY_ID)
    engine.skip()  # the first work interval of the new flow

    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK


# --- transition mode "confirm" -------------------------------------------------


def test_no_interval_is_upcoming_while_idle_or_running(engine):
    assert engine.upcoming_interval is None

    engine.start_flow(CATEGORY_ID)

    assert engine.upcoming_interval is None


def test_after_a_work_interval_the_engine_waits_with_a_short_break_upcoming(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)

    run_to_the_end(engine, clock)

    assert engine.current_interval is None
    assert engine.upcoming_interval == BaseInterval(
        kind=IntervalKind.SHORT_BREAK, category_id=None, planned_seconds=5 * 60
    )


def test_after_a_break_the_engine_waits_with_a_work_interval_upcoming(engine, clock):
    engine.start_flow(CATEGORY_ID)
    engine.skip()  # a short break starts

    run_to_the_end(engine, clock)

    assert engine.current_interval is None
    assert engine.upcoming_interval == BaseInterval(
        kind=IntervalKind.WORK, category_id=CATEGORY_ID, planned_seconds=25 * 60
    )


def test_after_the_fourth_work_interval_a_long_break_is_upcoming(engine, clock):
    engine.start_flow(CATEGORY_ID)
    for _ in range(3):
        engine.skip()  # a work interval
        engine.skip()  # the short break after it

    run_to_the_end(engine, clock)  # the fourth work interval

    assert engine.upcoming_interval == BaseInterval(
        kind=IntervalKind.LONG_BREAK, category_id=None, planned_seconds=15 * 60
    )


def test_no_time_is_counted_while_the_engine_waits(engine, clock):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)

    clock.advance(10 * 3600)
    engine.tick()

    assert engine.remaining_seconds() == 0
    assert len(engine.finished_intervals) == 1
    assert engine.upcoming_interval.kind == IntervalKind.SHORT_BREAK


def test_confirm_starts_the_upcoming_interval_from_the_moment_of_confirmation(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)
    clock.advance(3600)

    engine.confirm()

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=clock(),
    )
    assert engine.upcoming_interval is None
    assert engine.remaining_seconds() == 5 * 60


def test_confirm_after_a_break_starts_a_work_interval_of_the_flow_category(
    engine, clock
):
    engine.start_flow(CATEGORY_ID)
    engine.skip()
    run_to_the_end(engine, clock)

    engine.confirm()

    assert engine.current_interval.kind == IntervalKind.WORK
    assert engine.current_interval.category_id == CATEGORY_ID


def test_confirm_does_nothing_unless_the_engine_is_waiting(engine, clock):
    engine.confirm()
    assert engine.current_interval is None

    engine.start_flow(CATEGORY_ID)
    started_at = clock()
    clock.advance(100)
    engine.confirm()

    assert engine.current_interval.started_at == started_at
    assert engine.remaining_seconds() == 25 * 60 - 100


def test_a_settings_change_while_waiting_applies_to_the_interval_started_by_confirm(
    engine, clock, settings_repository
):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)

    settings_repository.set("short_break_minutes", 10)
    assert engine.upcoming_interval.planned_seconds == 10 * 60

    engine.confirm()
    assert engine.current_interval.planned_seconds == 10 * 60


def test_stop_while_waiting_ends_the_flow(engine, clock):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)

    engine.stop()
    engine.confirm()

    assert engine.upcoming_interval is None
    assert engine.current_interval is None
    assert len(engine.finished_intervals) == 1


def test_skip_and_pause_do_nothing_while_waiting(engine, clock):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)

    engine.skip()
    engine.pause()

    assert engine.current_interval is None
    assert engine.is_paused is False
    assert engine.upcoming_interval.kind == IntervalKind.SHORT_BREAK
    assert len(engine.finished_intervals) == 1


# --- transition mode "auto" -----------------------------------------------------


@pytest.fixture
def auto_engine(engine, settings_repository):
    settings_repository.set("transition_mode", "auto")
    return engine


def test_auto_starts_a_short_break_at_once_after_a_work_interval(auto_engine, clock):
    auto_engine.start_flow(CATEGORY_ID)

    run_to_the_end(auto_engine, clock)

    assert auto_engine.current_interval == RunningInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=clock(),
    )
    assert auto_engine.upcoming_interval is None
    assert [interval.status for interval in auto_engine.finished_intervals] == [
        IntervalStatus.COMPLETED
    ]


def test_auto_starts_a_work_interval_at_once_after_a_break(auto_engine, clock):
    auto_engine.start_flow(CATEGORY_ID)
    run_to_the_end(auto_engine, clock)  # the work interval; the break starts

    run_to_the_end(auto_engine, clock)  # the break

    assert auto_engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=CATEGORY_ID,
        planned_seconds=25 * 60,
        started_at=clock(),
    )
    assert auto_engine.upcoming_interval is None


def test_auto_keeps_the_flow_going_and_puts_a_long_break_after_the_fourth_work(
    auto_engine, clock
):
    auto_engine.start_flow(CATEGORY_ID)

    for _ in range(7):  # four work intervals and the three breaks between them
        run_to_the_end(auto_engine, clock)

    assert auto_engine.current_interval.kind == IntervalKind.LONG_BREAK
    assert len(auto_engine.finished_intervals) == 7


def test_auto_starts_the_next_interval_when_the_tick_notices_the_end(auto_engine, clock):
    auto_engine.start_flow(CATEGORY_ID)

    clock.advance(25 * 60 + 300)  # a late tick
    auto_engine.tick()

    assert auto_engine.current_interval.started_at == clock()
    assert auto_engine.remaining_seconds() == 5 * 60


def test_the_transition_mode_in_force_is_the_one_at_the_end_of_the_interval(
    engine, clock, settings_repository
):
    engine.start_flow(CATEGORY_ID)

    settings_repository.set("transition_mode", "auto")
    run_to_the_end(engine, clock)

    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK


# --- transition mode "mixed" -----------------------------------------------------


@pytest.fixture
def mixed_engine(engine, settings_repository):
    settings_repository.set("transition_mode", "mixed")
    return engine


def test_mixed_starts_a_break_at_once_after_a_work_interval(mixed_engine, clock):
    mixed_engine.start_flow(CATEGORY_ID)

    run_to_the_end(mixed_engine, clock)

    assert mixed_engine.current_interval == RunningInterval(
        kind=IntervalKind.SHORT_BREAK,
        category_id=None,
        planned_seconds=5 * 60,
        started_at=clock(),
    )
    assert mixed_engine.upcoming_interval is None


def test_mixed_waits_for_confirmation_after_a_break(mixed_engine, clock):
    mixed_engine.start_flow(CATEGORY_ID)
    run_to_the_end(mixed_engine, clock)  # the work interval; the break starts

    run_to_the_end(mixed_engine, clock)  # the break

    assert mixed_engine.current_interval is None
    assert mixed_engine.upcoming_interval == BaseInterval(
        kind=IntervalKind.WORK, category_id=CATEGORY_ID, planned_seconds=25 * 60
    )
    clock.advance(3600)
    mixed_engine.tick()
    assert mixed_engine.current_interval is None


def test_mixed_starts_the_work_interval_on_confirm(mixed_engine, clock):
    mixed_engine.start_flow(CATEGORY_ID)
    run_to_the_end(mixed_engine, clock)
    run_to_the_end(mixed_engine, clock)
    clock.advance(3600)

    mixed_engine.confirm()

    assert mixed_engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=CATEGORY_ID,
        planned_seconds=25 * 60,
        started_at=clock(),
    )


def test_mixed_starts_a_long_break_at_once_after_the_fourth_work_interval(
    mixed_engine, clock
):
    mixed_engine.start_flow(CATEGORY_ID)
    for _ in range(3):
        run_to_the_end(mixed_engine, clock)  # a work interval; its break starts
        run_to_the_end(mixed_engine, clock)  # the break
        mixed_engine.confirm()  # the next work interval

    run_to_the_end(mixed_engine, clock)  # the fourth work interval

    assert mixed_engine.current_interval.kind == IntervalKind.LONG_BREAK


# --- flow events ----------------------------------------------------------------


def test_starting_a_flow_emits_one_event_with_the_first_interval(
    engine, clock, events
):
    engine.start_flow(CATEGORY_ID)

    assert events == [
        FlowEvent(at=clock(), flow_started=True, started_interval=engine.current_interval)
    ]


def test_a_tick_that_changes_nothing_emits_no_event(engine, clock, events):
    engine.start_flow(CATEGORY_ID)
    events.clear()

    clock.advance(100)
    engine.tick()

    assert events == []


def test_completion_in_confirm_mode_emits_the_finished_interval_only(
    engine, clock, events
):
    engine.start_flow(CATEGORY_ID)
    events.clear()

    run_to_the_end(engine, clock)

    assert events == [
        FlowEvent(at=clock(), finished_interval=engine.finished_intervals[0])
    ]


def test_completion_in_auto_mode_emits_the_finished_and_the_started_interval_together(
    auto_engine, clock, events
):
    auto_engine.start_flow(CATEGORY_ID)
    events.clear()

    run_to_the_end(auto_engine, clock)

    assert events == [
        FlowEvent(
            at=clock(),
            finished_interval=auto_engine.finished_intervals[0],
            started_interval=auto_engine.current_interval,
        )
    ]


def test_confirm_emits_the_started_interval_only(engine, clock, events):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)
    events.clear()

    engine.confirm()

    assert events == [FlowEvent(at=clock(), started_interval=engine.current_interval)]


def test_skip_emits_the_skipped_and_the_started_interval_together(engine, clock, events):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)
    events.clear()

    engine.skip()

    assert events == [
        FlowEvent(
            at=clock(),
            finished_interval=engine.finished_intervals[0],
            started_interval=engine.current_interval,
        )
    ]


def test_stop_emits_the_stopped_interval_and_the_end_of_the_flow(engine, clock, events):
    engine.start_flow(CATEGORY_ID)
    clock.advance(600)
    events.clear()

    engine.stop()

    assert events == [
        FlowEvent(
            at=clock(),
            finished_interval=engine.finished_intervals[0],
            flow_ended=True,
        )
    ]


def test_stop_while_waiting_emits_the_end_of_the_flow_only(engine, clock, events):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end(engine, clock)
    events.clear()

    engine.stop()

    assert events == [FlowEvent(at=clock(), flow_ended=True)]


def test_operations_that_change_nothing_emit_no_event(engine, clock, events):
    engine.skip()
    engine.stop()
    engine.confirm()
    engine.pause()
    engine.resume()
    engine.tick()
    engine.start_flow(CATEGORY_ID)
    events.clear()

    engine.pause()
    engine.resume()
    engine.confirm()

    assert events == []


def test_the_engine_works_without_a_listener(settings_repository, clock):
    engine = Engine(get_settings=settings_repository.get_all, clock=clock)

    engine.start_flow(CATEGORY_ID)
    engine.skip()
    engine.stop()

    assert len(engine.finished_intervals) == 2


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

import pytest
from fermata.engine import Engine
from fermata.intervals import IntervalKind
from fermata.scenarios import Scenario, ScenarioRow
from fermata.storage.settings import Settings
from fermata.ui.waiting_view_model import WaitingViewModel


@pytest.fixture
def engine(clock):
    return Engine(get_settings=Settings, clock=clock)  # confirmation is awaited by default


@pytest.fixture
def waiting_view_model(engine):
    return WaitingViewModel(engine)


def run_to_the_end(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


def confirm_to_the_end(engine, clock, count):
    """Let `count` intervals run to their end, confirming each one that follows."""
    for _ in range(count):
        run_to_the_end(engine, clock)
        engine.confirm()


# --- what comes next -------------------------------------------------------------


def test_a_break_follows_the_first_work_interval(waiting_view_model, engine, clock):
    engine.start_flow(1)
    run_to_the_end(engine, clock)

    assert waiting_view_model.next_title() == "Next: Short break"


def test_the_second_work_interval_follows_the_break_with_its_number(
    waiting_view_model, engine, clock
):
    engine.start_flow(1)
    confirm_to_the_end(engine, clock, 1)
    run_to_the_end(engine, clock)

    assert waiting_view_model.next_title() == "Next: Work · 2"


def test_a_long_break_follows_every_nth_work_interval(waiting_view_model, engine, clock):
    engine.start_flow(1)
    confirm_to_the_end(engine, clock, 6)  # three work intervals and three short breaks
    run_to_the_end(engine, clock)  # the fourth work interval

    assert waiting_view_model.next_title() == "Next: Long break"


def test_the_work_interval_after_a_long_break_goes_on_with_the_numbering(
    waiting_view_model, engine, clock
):
    engine.start_flow(1)
    confirm_to_the_end(engine, clock, 7)  # four work intervals, three short breaks
    run_to_the_end(engine, clock)  # the long break

    assert waiting_view_model.next_title() == "Next: Work · 5"


def test_a_skipped_work_interval_is_counted_in_the_numbering(
    waiting_view_model, engine, clock
):
    engine.start_flow(1)
    engine.skip()  # the first work interval, then its break runs
    run_to_the_end(engine, clock)

    assert waiting_view_model.next_title() == "Next: Work · 2"


def test_a_scenario_names_the_next_work_interval_out_of_the_total(
    waiting_view_model, engine, clock
):
    scenario = Scenario("Day", (ScenarioRow(2, 2), ScenarioRow(3, 1)), repeat_count=2)
    engine.start_scenario(scenario)
    confirm_to_the_end(engine, clock, 1)
    run_to_the_end(engine, clock)

    assert waiting_view_model.next_title() == "Next: Work · 2/6"


def test_a_break_in_a_scenario_is_named_without_numbers(waiting_view_model, engine, clock):
    scenario = Scenario("Day", (ScenarioRow(2, 2),))
    engine.start_scenario(scenario)
    run_to_the_end(engine, clock)

    assert waiting_view_model.next_title() == "Next: Short break"


# --- the buttons -----------------------------------------------------------------


def test_next_starts_the_upcoming_interval(waiting_view_model, engine, clock):
    engine.start_flow(1)
    run_to_the_end(engine, clock)

    waiting_view_model.confirm()

    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK


def test_stop_ends_the_flow_while_waiting(waiting_view_model, engine, clock):
    engine.start_flow(1)
    run_to_the_end(engine, clock)

    waiting_view_model.stop()

    assert engine.upcoming_interval is None
    assert engine.current_interval is None

import pytest
from fermata.engine import Engine, FlowEvent
from fermata.intervals import IntervalKind, IntervalStatus, SessionSummary
from fermata.scenarios import Scenario, ScenarioRow
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.settings import SettingsRepository

WORK, PERSONAL = 2, 3  # the engine only carries the ids; it does not look categories up


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


@pytest.fixture
def auto_engine(engine, settings_repository):
    settings_repository.set("transition_mode", "auto")
    return engine


@pytest.fixture
def example():
    """The example of the spec: (Work × 2, Personal × 1) × 2, six work intervals."""
    return Scenario(
        name="Work day",
        rows=(ScenarioRow(WORK, 2), ScenarioRow(PERSONAL, 1)),
        repeat_count=2,
    )


def run_to_the_end(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


def run_until_the_session_ends(engine, clock):
    """Let intervals end, confirming where the engine waits, until nothing is left."""
    for _ in range(50):
        if engine.current_interval is not None:
            run_to_the_end(engine, clock)
        elif engine.upcoming_interval is not None:
            engine.confirm()
        else:
            return
    raise AssertionError("the session did not end")


def work_intervals(engine):
    return [i for i in engine.finished_intervals if i.kind == IntervalKind.WORK]


# --- starting ------------------------------------------------------------------


def test_a_scenario_begins_with_the_category_of_its_first_row(engine, example, clock):
    engine.start_scenario(example)

    interval = engine.current_interval
    assert (interval.kind, interval.category_id) == (IntervalKind.WORK, WORK)
    assert interval.planned_seconds == 25 * 60
    assert interval.started_at == clock()


def test_a_scenario_takes_its_work_length_from_its_override(engine, example):
    scenario = Scenario("Short", example.rows, work_minutes=10)

    engine.start_scenario(scenario)

    assert engine.current_interval.planned_seconds == 600


# --- the order of the intervals ------------------------------------------------


def test_work_intervals_take_the_categories_of_the_rows_in_order(auto_engine, example, clock):
    auto_engine.start_scenario(example)
    run_until_the_session_ends(auto_engine, clock)

    categories = [i.category_id for i in work_intervals(auto_engine)]
    assert categories == [WORK, WORK, PERSONAL, WORK, WORK, PERSONAL]


def test_breaks_follow_the_global_rules_with_a_long_break_strictly_by_n(
    auto_engine, example, clock
):
    auto_engine.start_scenario(example)
    run_until_the_session_ends(auto_engine, clock)

    kinds = [i.kind for i in auto_engine.finished_intervals]
    assert kinds == [
        IntervalKind.WORK,
        IntervalKind.SHORT_BREAK,
        IntervalKind.WORK,
        IntervalKind.SHORT_BREAK,
        IntervalKind.WORK,
        IntervalKind.SHORT_BREAK,
        IntervalKind.WORK,
        IntervalKind.LONG_BREAK,  # after the fourth work interval, not after a repetition
        IntervalKind.WORK,
        IntervalKind.SHORT_BREAK,
        IntervalKind.WORK,
    ]


def test_the_overrides_of_the_scenario_set_the_breaks(auto_engine, example, clock):
    scenario = Scenario(
        "Short",
        example.rows,
        repeat_count=2,
        short_break_minutes=1,
        long_break_minutes=2,
        long_break_every=2,
    )
    auto_engine.start_scenario(scenario)
    run_until_the_session_ends(auto_engine, clock)

    breaks = [
        (i.kind, i.planned_seconds)
        for i in auto_engine.finished_intervals
        if i.kind != IntervalKind.WORK
    ]
    assert breaks == [
        (IntervalKind.SHORT_BREAK, 60),
        (IntervalKind.LONG_BREAK, 120),
        (IntervalKind.SHORT_BREAK, 60),
        (IntervalKind.LONG_BREAK, 120),
        (IntervalKind.SHORT_BREAK, 60),
    ]


def test_values_that_are_not_overridden_are_read_from_the_global_settings_when_needed(
    engine, settings_repository, example, clock
):
    scenario = Scenario("Short", example.rows, work_minutes=10)
    engine.start_scenario(scenario)
    settings_repository.set("short_break_minutes", 9)
    settings_repository.set("work_minutes", 40)

    run_to_the_end(engine, clock)
    engine.confirm()  # the break
    run_to_the_end(engine, clock)
    engine.confirm()  # the next work interval

    breaks = [i for i in engine.finished_intervals if i.kind != IntervalKind.WORK]
    assert breaks[0].planned_seconds == 9 * 60  # global value, read at the start of the break
    assert engine.current_interval.planned_seconds == 600  # the override still wins


@pytest.mark.parametrize(
    ("mode", "after_work", "after_break"),
    [
        ("confirm", None, None),
        ("mixed", IntervalKind.SHORT_BREAK, None),
        ("auto", IntervalKind.SHORT_BREAK, IntervalKind.WORK),
    ],
)
def test_the_transition_modes_work_as_in_a_flow(
    engine, settings_repository, example, clock, mode, after_work, after_break
):
    settings_repository.set("transition_mode", mode)
    engine.start_scenario(example)

    run_to_the_end(engine, clock)
    kind_after_work = engine.current_interval and engine.current_interval.kind
    if engine.current_interval is None:
        engine.confirm()
    run_to_the_end(engine, clock)
    kind_after_break = engine.current_interval and engine.current_interval.kind

    assert kind_after_work == after_work
    assert kind_after_break == after_break


# --- the end of the session ----------------------------------------------------


def test_no_break_follows_the_last_work_interval(auto_engine, example, clock):
    auto_engine.start_scenario(example)

    run_until_the_session_ends(auto_engine, clock)

    assert auto_engine.current_interval is None
    assert auto_engine.finished_intervals[-1].kind == IntervalKind.WORK
    assert auto_engine.finished_intervals[-1].status == IntervalStatus.COMPLETED


def test_the_session_ends_at_once_also_when_confirmation_is_awaited(engine, example, clock):
    scenario = Scenario("One", (ScenarioRow(WORK, 1),))
    engine.start_scenario(scenario)

    run_to_the_end(engine, clock)

    assert engine.current_interval is None
    assert engine.upcoming_interval is None


def test_the_summary_counts_the_work_intervals_done(auto_engine, example, clock):
    auto_engine.start_scenario(example)

    run_until_the_session_ends(auto_engine, clock)

    assert auto_engine.summary() == SessionSummary(done_count=6, skipped_count=0)


def test_skipping_the_last_work_interval_ends_the_session_and_counts_as_skipped(
    auto_engine, example, clock
):
    auto_engine.start_scenario(example)
    for _ in range(10):  # five work intervals and the breaks between them
        run_to_the_end(auto_engine, clock)
    assert auto_engine.current_interval.kind == IntervalKind.WORK

    clock.advance(60)
    auto_engine.skip()

    assert auto_engine.current_interval is None
    assert auto_engine.finished_intervals[-1].status == IntervalStatus.SKIPPED
    assert auto_engine.summary() == SessionSummary(done_count=5, skipped_count=1)


def test_skipping_an_earlier_work_interval_starts_its_break(engine, example, clock):
    engine.start_scenario(example)
    clock.advance(60)

    engine.skip()

    assert engine.current_interval.kind == IntervalKind.SHORT_BREAK
    assert engine.summary() is None


def test_there_is_no_summary_while_the_session_runs(engine, example):
    engine.start_scenario(example)

    assert engine.summary() is None


def test_stopping_a_scenario_gives_no_summary(engine, example, clock):
    engine.start_scenario(example)
    clock.advance(60)

    engine.stop()

    assert engine.current_interval is None
    assert engine.summary() is None


def test_a_flow_has_no_summary_and_never_ends_by_itself(auto_engine, clock):
    auto_engine.start_flow(WORK)
    for _ in range(40):
        run_to_the_end(auto_engine, clock)

    assert auto_engine.current_interval is not None
    assert auto_engine.summary() is None


def test_a_new_session_clears_the_summary_and_the_history(auto_engine, example, clock):
    auto_engine.start_scenario(example)
    run_until_the_session_ends(auto_engine, clock)

    auto_engine.start_flow(WORK)

    assert auto_engine.summary() is None
    assert auto_engine.finished_intervals == []


def test_a_flow_after_a_scenario_keeps_one_category(auto_engine, example, clock):
    auto_engine.start_scenario(example)
    run_until_the_session_ends(auto_engine, clock)

    auto_engine.start_flow(PERSONAL)
    for _ in range(4):
        run_to_the_end(auto_engine, clock)

    assert {i.category_id for i in work_intervals(auto_engine)} == {PERSONAL}


def test_a_scenario_after_a_flow_starts_from_its_first_row(auto_engine, example, clock):
    auto_engine.start_flow(PERSONAL)
    run_to_the_end(auto_engine, clock)

    auto_engine.start_scenario(example)

    assert auto_engine.current_interval.category_id == WORK
    assert auto_engine.finished_intervals == []


# --- events --------------------------------------------------------------------


def test_starting_a_scenario_emits_one_event_carrying_the_scenario(
    engine, example, clock, events
):
    engine.start_scenario(example)

    assert events == [
        FlowEvent(
            at=clock(),
            flow_started=True,
            scenario=example,
            started_interval=engine.current_interval,
        )
    ]


def test_the_last_work_interval_ends_the_session_in_one_event(
    auto_engine, example, clock, events
):
    auto_engine.start_scenario(example)
    for _ in range(10):
        run_to_the_end(auto_engine, clock)
    events.clear()

    run_to_the_end(auto_engine, clock)

    assert events == [
        FlowEvent(
            at=clock(),
            finished_interval=auto_engine.finished_intervals[-1],
            flow_ended=True,
            session_completed=True,
        )
    ]


def test_skipping_the_last_work_interval_ends_the_session_in_one_event(
    auto_engine, example, clock, events
):
    auto_engine.start_scenario(example)
    for _ in range(10):
        run_to_the_end(auto_engine, clock)
    events.clear()

    auto_engine.skip()

    assert events == [
        FlowEvent(
            at=clock(),
            finished_interval=auto_engine.finished_intervals[-1],
            flow_ended=True,
            session_completed=True,
        )
    ]


def test_stopping_a_scenario_ends_the_session_but_not_as_completed(
    engine, example, clock, events
):
    engine.start_scenario(example)
    events.clear()

    engine.stop()

    (event,) = events
    assert (event.flow_ended, event.session_completed) == (True, False)


# --- the scenario of the session ---------------------------------------------------


def test_there_is_no_scenario_before_a_session_and_during_a_flow(engine):
    assert engine.scenario is None

    engine.start_flow(WORK)

    assert engine.scenario is None


def test_the_scenario_is_the_one_of_the_session_and_outlives_it(auto_engine, example, clock):
    auto_engine.start_scenario(example)

    assert auto_engine.scenario == example

    run_until_the_session_ends(auto_engine, clock)

    assert auto_engine.scenario == example


def test_a_flow_forgets_the_scenario(engine, example):
    engine.start_scenario(example)

    engine.start_flow(WORK)

    assert engine.scenario is None

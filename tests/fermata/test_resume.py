"""Resuming a scenario session after the app was closed in the middle of it.

A crash is simulated by building the application parts again on the same database file while
the session of the first build was never stopped.
"""

import pytest
from fermata.intervals import IntervalKind, SessionSummary
from fermata.storage.db import Db
from fermata.wiring import build_components

AUTO = dict(
    work_minutes="25",
    short_break_minutes="5",
    long_break_minutes="15",
    long_break_every="4",
    transition_mode="auto",
    blink=True,
    sound=True,
)


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "fermata.db"


@pytest.fixture
def components(database_path, clock):
    return build_components(database_path, clock)


def restart(database_path, clock):
    """What starting the app again does after it was closed."""
    return build_components(database_path, clock)


def make_auto(components):
    assert components.settings_view_model.save(**AUTO) is None


def make_example(components, name="Day"):
    """(Work × 2, Personal × 1) × 2, six work intervals; return its id and the categories."""
    components.categories_view_model.add("Work", "#112233")
    components.categories_view_model.add("Personal", "#445566")
    categories = {c.name: c.id for c in components.categories_view_model.categories()}
    editor = components.scenarios_view_model.new_editor()
    editor.set_name(name)
    editor.set_row_category(0, categories["Work"])
    editor.set_row_count(0, "2")
    editor.add_row()
    editor.set_row_category(1, categories["Personal"])
    editor.set_repeat_count("2")
    assert editor.save() is None
    return editor.saved_scenario_id, categories


def start_example(components, name="Day"):
    scenario_id, categories = make_example(components, name)
    components.scenarios_view_model.start(scenario_id)
    return scenario_id, categories


def run_to_the_end(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


def run_until_the_session_ends(engine, clock):
    for _ in range(50):
        if engine.current_interval is not None:
            run_to_the_end(engine, clock)
        elif engine.upcoming_interval is not None:
            engine.confirm()
        else:
            return
    raise AssertionError("the session did not end")


def stored_sessions(database_path):
    return Db.open(database_path).query("SELECT * FROM session ORDER BY id", mapper=dict)


def stored_intervals(database_path):
    return Db.open(database_path).query(
        "SELECT position, kind, category_id, status, actual_seconds FROM interval"
        " ORDER BY session_id, position",
        mapper=dict,
    )


def statuses(database_path):
    return [row["status"] for row in stored_intervals(database_path)]


# --- when it is offered -----------------------------------------------------------


def test_nothing_is_offered_on_a_clean_start(components):
    assert components.resumption is None


def test_a_scenario_closed_in_its_first_work_interval_is_offered(
    components, database_path, clock
):
    start_example(components)
    clock.advance(600)

    restarted = restart(database_path, clock)

    assert restarted.resumption.question() == 'Resume scenario "Day" from interval 1 of 6?'


def test_the_question_names_the_work_interval_to_start_again(
    components, database_path, clock
):
    make_auto(components)
    start_example(components)
    for _ in range(4):  # two work intervals and their breaks
        run_to_the_end(components.engine, clock)

    restarted = restart(database_path, clock)

    assert restarted.resumption.question() == 'Resume scenario "Day" from interval 3 of 6?'


def test_skipped_work_intervals_count_as_passed(components, database_path, clock):
    start_example(components)
    for _ in range(4):  # skip a work interval, its break, the next work interval, its break
        components.engine.skip()

    restarted = restart(database_path, clock)

    assert restarted.resumption.question() == 'Resume scenario "Day" from interval 3 of 6?'


def test_a_scenario_closed_while_waiting_for_confirmation_is_offered(
    components, database_path, clock
):
    start_example(components)
    run_to_the_end(components.engine, clock)  # the first work interval; confirmation awaited
    assert components.engine.upcoming_interval is not None

    restarted = restart(database_path, clock)

    assert restarted.resumption.question() == 'Resume scenario "Day" from interval 2 of 6?'


def test_a_flow_is_never_offered(components, database_path, clock):
    components.home_view_model.start()
    clock.advance(600)

    assert restart(database_path, clock).resumption is None


def test_a_finished_scenario_is_not_offered(components, database_path, clock):
    make_auto(components)
    start_example(components)
    run_until_the_session_ends(components.engine, clock)

    assert restart(database_path, clock).resumption is None


def test_a_stopped_scenario_is_not_offered(components, database_path, clock):
    start_example(components)
    components.engine.stop()

    assert restart(database_path, clock).resumption is None


def test_it_is_offered_again_until_it_is_answered(components, database_path, clock):
    start_example(components)
    restart(database_path, clock)  # the question was shown, but the window was closed

    again = restart(database_path, clock)

    assert again.resumption.question() == 'Resume scenario "Day" from interval 1 of 6?'


def test_only_the_latest_session_is_offered(components, database_path, clock):
    start_example(components)
    unanswered = restart(database_path, clock)
    unanswered.home_view_model.start()  # a newer session: a flow
    unanswered.engine.stop()

    assert restart(database_path, clock).resumption is None


# --- saying yes ------------------------------------------------------------------


def test_the_work_interval_starts_again_from_the_beginning(components, database_path, clock):
    make_auto(components)
    _, categories = start_example(components)
    for _ in range(4):
        run_to_the_end(components.engine, clock)
    clock.advance(600)  # ten minutes into the third work interval, then the window closes
    restarted = restart(database_path, clock)
    clock.advance(3600)

    restarted.resumption.resume()

    interval = restarted.engine.current_interval
    assert (interval.kind, interval.category_id) == (IntervalKind.WORK, categories["Personal"])
    assert interval.planned_seconds == 25 * 60
    assert interval.started_at == clock()
    assert restarted.engine.scenario.name == "Day"


def test_an_interrupted_break_is_not_repeated(components, database_path, clock):
    make_auto(components)
    _, categories = start_example(components)
    for _ in range(3):  # two work intervals and the first break; the second break runs
        run_to_the_end(components.engine, clock)
    assert components.engine.current_interval.kind == IntervalKind.SHORT_BREAK
    restarted = restart(database_path, clock)

    restarted.resumption.resume()

    interval = restarted.engine.current_interval
    assert (interval.kind, interval.category_id) == (IntervalKind.WORK, categories["Personal"])


def test_waiting_for_confirmation_resumes_with_the_next_work_interval(
    components, database_path, clock
):
    _, categories = start_example(components)
    run_to_the_end(components.engine, clock)  # the first work interval; its break is awaited
    restarted = restart(database_path, clock)

    restarted.resumption.resume()

    interval = restarted.engine.current_interval
    assert (interval.kind, interval.category_id) == (IntervalKind.WORK, categories["Work"])


def test_the_same_session_goes_on_in_the_database(components, database_path, clock):
    make_auto(components)
    start_example(components)
    for _ in range(4):
        run_to_the_end(components.engine, clock)
    restarted = restart(database_path, clock)
    assert [row["status"] for row in stored_sessions(database_path)] == ["interrupted"]

    restarted.resumption.resume()

    (session,) = stored_sessions(database_path)
    assert (session["status"], session["ended_at"]) == ("running", None)
    rows = stored_intervals(database_path)
    assert [row["position"] for row in rows] == [1, 2, 3, 4, 5, 6]
    # The interrupted interval stays as it was; the work interval starts again as a new row.
    assert [row["status"] for row in rows] == [
        "completed", "completed", "completed", "completed", "interrupted", None,
    ]  # fmt: skip
    assert rows[4]["actual_seconds"] is None
    assert (rows[5]["kind"], rows[5]["category_id"]) == (rows[4]["kind"], rows[4]["category_id"])


def test_a_resumed_scenario_runs_to_its_end_and_counts_what_was_done_before(
    components, database_path, clock
):
    make_auto(components)
    start_example(components)
    for _ in range(4):
        run_to_the_end(components.engine, clock)
    restarted = restart(database_path, clock)
    restarted.resumption.resume()

    run_until_the_session_ends(restarted.engine, clock)

    assert restarted.engine.summary() == SessionSummary(done_count=6, skipped_count=0)
    (session,) = stored_sessions(database_path)
    assert session["status"] == "completed"
    kinds = [row["kind"] for row in stored_intervals(database_path)]
    # The long break still follows the fourth work interval that counts.
    assert kinds.count("long_break") == 1
    assert statuses(database_path).count("interrupted") == 1


def test_skipped_work_intervals_stay_skipped_in_the_summary(components, database_path, clock):
    make_auto(components)
    start_example(components)
    for _ in range(4):
        components.engine.skip()
    restarted = restart(database_path, clock)
    restarted.resumption.resume()

    run_until_the_session_ends(restarted.engine, clock)

    assert restarted.engine.summary() == SessionSummary(done_count=4, skipped_count=2)


def test_closing_a_resumed_session_again_offers_it_again(components, database_path, clock):
    make_auto(components)
    start_example(components)
    for _ in range(4):
        run_to_the_end(components.engine, clock)
    restarted = restart(database_path, clock)
    restarted.resumption.resume()
    clock.advance(60)

    again = restart(database_path, clock)

    assert again.resumption.question() == 'Resume scenario "Day" from interval 3 of 6?'


def test_the_snapshot_is_used_not_the_scenario_as_it_is_now(components, database_path, clock):
    scenario_id, categories = make_example(components)
    editor = components.scenarios_view_model.editor_for(scenario_id)
    editor.set_override("work_minutes", 10)
    assert editor.save() is None
    components.scenarios_view_model.start(scenario_id)
    components.scenarios_view_model.delete(scenario_id)
    components.settings_view_model.save(**{**AUTO, "work_minutes": "40"})
    restarted = restart(database_path, clock)

    restarted.resumption.resume()

    assert restarted.engine.current_interval.planned_seconds == 10 * 60


# --- saying no -------------------------------------------------------------------


def test_declining_ends_the_session_as_stopped(components, database_path, clock):
    start_example(components)
    restarted = restart(database_path, clock)

    restarted.resumption.decline()

    (session,) = stored_sessions(database_path)
    assert session["status"] == "stopped"
    assert restarted.engine.current_interval is None
    assert statuses(database_path) == ["interrupted"]


def test_a_declined_session_is_not_offered_again(components, database_path, clock):
    start_example(components)
    restart(database_path, clock).resumption.decline()

    assert restart(database_path, clock).resumption is None

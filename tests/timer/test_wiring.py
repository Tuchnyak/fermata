import pytest
from timer.intervals import IntervalKind
from timer.storage.db import Db
from timer.wiring import build_components


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "timer.db"


@pytest.fixture
def components(database_path, clock):
    return build_components(database_path, clock)


def stored_sessions(database_path):
    return Db.open(database_path).query(
        "SELECT * FROM session ORDER BY id", mapper=dict
    )


def stored_intervals(database_path):
    return Db.open(database_path).query(
        "SELECT * FROM interval ORDER BY session_id, position", mapper=dict
    )


def start_flow(components):
    category = components.categories_view_model.categories()[0]
    components.home_view_model.select(category.id)
    components.home_view_model.start()


def test_creates_the_database_with_its_schema(database_path, components):
    assert database_path.exists()
    categories = components.categories_view_model.categories()
    assert [category.name for category in categories] == ["None"]


def test_starting_a_flow_writes_a_running_session_and_interval(
    database_path, components
):
    start_flow(components)

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["running"]
    assert [(i["kind"], i["status"]) for i in intervals] == [("work", None)]


def test_stopping_the_flow_closes_its_rows(database_path, clock, components):
    start_flow(components)
    clock.advance(60)

    components.engine.stop()

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["stopped"]
    assert [(i["status"], i["actual_seconds"]) for i in intervals] == [("stopped", 60)]


def test_the_category_of_the_previous_flow_is_preselected_after_stop(components):
    components.categories_view_model.add("Study", "#112233")
    category = next(
        category
        for category in components.categories_view_model.categories()
        if category.name == "Study"
    )
    components.home_view_model.select(category.id)
    components.home_view_model.start()
    components.engine.stop()

    components.home_view_model.preselect()

    assert components.home_view_model.selected_category().id == category.id


def test_settings_saved_in_the_ui_apply_to_the_next_flow(components):
    message = components.settings_view_model.save(
        work_minutes="30",
        short_break_minutes="5",
        long_break_minutes="15",
        long_break_every="4",
        transition_mode="confirm",
        blink=True,
    )
    assert message is None

    start_flow(components)

    interval = components.engine.current_interval
    assert interval.kind == IntervalKind.WORK
    assert interval.planned_seconds == 30 * 60


def test_an_interval_left_running_is_interrupted_by_the_next_start(
    database_path, clock, components
):
    start_flow(components)
    clock.advance(60)
    # The window is closed here: nothing stops the flow.

    restarted = build_components(database_path, clock)

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["interrupted"]
    assert [(i["status"], i["actual_seconds"]) for i in intervals] == [
        ("interrupted", None)
    ]
    assert restarted.engine.current_interval is None

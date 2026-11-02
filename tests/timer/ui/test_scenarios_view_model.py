import pytest
from timer.engine import Engine
from timer.scenarios import Scenario, ScenarioRow
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.scenarios import ScenarioRepository
from timer.storage.settings import SettingsRepository
from timer.ui.scenario_editor_view_model import ScenarioEditorViewModel
from timer.ui.scenarios_view_model import ScenariosViewModel


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def scenario_repository(db):
    return ScenarioRepository(db)


@pytest.fixture
def settings_repository(db):
    return SettingsRepository(db)


@pytest.fixture
def engine(settings_repository, clock):
    return Engine(get_settings=settings_repository.get_all, clock=clock)


@pytest.fixture
def scenarios_view_model(
    scenario_repository, category_repository, settings_repository, engine
):
    return ScenariosViewModel(
        scenario_repository, category_repository, settings_repository, engine
    )


@pytest.fixture
def work(category_repository):
    return category_repository.create("Work", "#112233")


@pytest.fixture
def personal(category_repository):
    return category_repository.create("Personal", "#445566")


@pytest.fixture
def example(scenario_repository, work, personal):
    """The example of the spec: (Work × 2, Personal × 1) × 2."""
    return scenario_repository.create(
        Scenario(
            "Work day",
            (ScenarioRow(work.id, 2), ScenarioRow(personal.id, 1)),
            repeat_count=2,
        )
    )


# --- the list --------------------------------------------------------------------


def test_there_are_no_scenarios_at_first(scenarios_view_model):
    assert scenarios_view_model.scenarios() == []


def test_the_scenarios_are_listed_by_name(scenarios_view_model, scenario_repository, work):
    for name in ["b", "A", "c"]:
        scenario_repository.create(Scenario(name, (ScenarioRow(work.id, 1),)))

    names = [scenario.name for scenario in scenarios_view_model.scenarios()]

    assert names == ["A", "b", "c"]


def test_a_scenario_is_described_by_its_work_intervals_and_total_time(
    scenarios_view_model, example
):
    assert scenarios_view_model.describe(example) == "6 work intervals · ~3h 05m"


def test_the_description_follows_the_overrides_and_the_global_settings(
    scenarios_view_model, scenario_repository, settings_repository, work
):
    settings_repository.set("work_minutes", 40)
    scenario = scenario_repository.create(
        Scenario("Pair", (ScenarioRow(work.id, 2),), short_break_minutes=10)
    )

    assert scenarios_view_model.describe(scenario) == "2 work intervals · ~1h 30m"


# --- deleting --------------------------------------------------------------------


def test_a_scenario_is_deleted(scenarios_view_model, scenario_repository, example):
    scenarios_view_model.delete(example.id)

    assert scenario_repository.list_all() == []


# --- starting --------------------------------------------------------------------


def test_a_scenario_is_started_with_its_first_row(scenarios_view_model, engine, example, work):
    scenarios_view_model.start(example.id)

    assert engine.current_interval.category_id == work.id
    assert engine.current_interval.planned_seconds == 25 * 60


def test_a_scenario_can_be_started_while_the_timer_is_idle(scenarios_view_model):
    assert scenarios_view_model.can_start() is True


def test_a_scenario_cannot_be_started_while_a_session_runs(
    scenarios_view_model, engine, example
):
    scenarios_view_model.start(example.id)

    assert scenarios_view_model.can_start() is False


def test_a_scenario_cannot_be_started_while_the_timer_waits(
    scenarios_view_model, engine, example, clock
):
    engine.start_flow(1)
    clock.advance(25 * 60)
    engine.tick()  # confirmation is awaited

    assert scenarios_view_model.can_start() is False


def test_starting_while_a_session_runs_changes_nothing(
    scenarios_view_model, engine, example, work
):
    engine.start_flow(1)

    scenarios_view_model.start(example.id)

    assert engine.current_interval.category_id == 1


# --- the editor ------------------------------------------------------------------


def test_the_editor_for_a_new_scenario_is_blank(scenarios_view_model):
    editor = scenarios_view_model.new_editor()

    assert isinstance(editor, ScenarioEditorViewModel)
    assert editor.name() == ""


def test_the_editor_for_an_existing_scenario_holds_it(scenarios_view_model, example):
    editor = scenarios_view_model.editor_for(example.id)

    assert editor.name() == "Work day"
    assert editor.repeat_count() == 2


# --- a running session and its scenario ------------------------------------------


def test_deleting_the_scenario_of_a_running_session_changes_nothing_for_the_session(
    scenarios_view_model, engine, example, work, personal, clock
):
    scenarios_view_model.start(example.id)

    scenarios_view_model.delete(example.id)

    categories = []
    for _ in range(11):  # six work intervals and the five breaks between them
        if engine.current_interval is None:
            engine.confirm()
        if engine.current_interval.kind.value == "work":
            categories.append(engine.current_interval.category_id)
        clock.advance(engine.remaining_seconds())
        engine.tick()
    assert categories == [work.id, work.id, personal.id, work.id, work.id, personal.id]

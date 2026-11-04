import pytest
from fermata.engine import Engine
from fermata.i18n import t
from fermata.intervals import IntervalKind, RunningInterval
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.scenarios import ScenarioRepository
from fermata.storage.sessions import SessionRepository
from fermata.storage.settings import Settings
from fermata.scenarios import Scenario, ScenarioRow
from fermata.ui.home_view_model import HomeMode, HomeViewModel, StartKind


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def engine(clock):
    return Engine(get_settings=Settings, clock=clock)


@pytest.fixture
def work_category(category_repository):
    return category_repository.create("Work", "#112233")


@pytest.fixture
def reading_category(category_repository):
    return category_repository.create("Reading", "#445566")


@pytest.fixture
def scenario_repository(db):
    return ScenarioRepository(db)


def make_home_view_model(
    category_repository, session_repository, engine, scenario_repository
):
    return HomeViewModel(
        category_repository, session_repository, engine, scenario_repository
    )


@pytest.fixture
def home_view_model(
    category_repository, session_repository, engine, scenario_repository
):
    return make_home_view_model(
        category_repository, session_repository, engine, scenario_repository
    )


def record_flow(session_repository, category, started_at):
    """A flow of the given category, as the recorder leaves it in the history."""
    session_id = session_repository.create_flow(started_at)
    session_repository.start_interval(
        session_id,
        1,
        RunningInterval(
            kind=IntervalKind.WORK,
            category_id=category.id,
            planned_seconds=25 * 60,
            started_at=started_at,
        ),
    )


# --- what the home screen shows ---------------------------------------------------


def test_the_home_screen_is_idle_before_a_flow_starts(home_view_model):
    assert home_view_model.mode() == HomeMode.IDLE


def test_the_home_screen_shows_the_running_flow(home_view_model):
    home_view_model.start()

    assert home_view_model.mode() == HomeMode.RUNNING


def test_the_home_screen_is_idle_again_after_the_flow_is_stopped(
    home_view_model, engine
):
    home_view_model.start()

    engine.stop()

    assert home_view_model.mode() == HomeMode.IDLE


def test_the_home_screen_waits_when_an_interval_has_ended_and_confirmation_is_awaited(
    home_view_model, engine, clock
):
    home_view_model.start()

    clock.advance(25 * 60)
    engine.tick()

    assert home_view_model.mode() == HomeMode.WAITING


# --- the categories to choose from -------------------------------------------


def test_the_categories_are_the_active_ones_with_none_first(
    home_view_model, category_repository
):
    category_repository.create("Banana", "#112233")
    category_repository.create("Apple", "#112233")
    archived = category_repository.create("Cherry", "#112233")
    category_repository.archive(archived.id)

    names = [category.name for category in home_view_model.categories()]

    assert names == ["None", "Apple", "Banana"]


# --- the preselected category --------------------------------------------------


def test_none_is_preselected_when_there_was_no_flow_before(home_view_model):
    assert home_view_model.selected_category().is_system is True


def test_the_category_of_the_previous_flow_is_preselected(
    category_repository, session_repository, engine, work_category, clock, scenario_repository
):
    record_flow(session_repository, work_category, clock())

    home_view_model = make_home_view_model(
        category_repository, session_repository, engine, scenario_repository
    )

    assert home_view_model.selected_category() == work_category


def test_the_most_recent_flow_decides_the_preselection(
    category_repository, session_repository, engine, work_category, reading_category, clock, scenario_repository
):
    record_flow(session_repository, work_category, clock())
    clock.advance(3600)
    record_flow(session_repository, reading_category, clock())

    home_view_model = make_home_view_model(
        category_repository, session_repository, engine, scenario_repository
    )

    assert home_view_model.selected_category() == reading_category


def test_none_is_preselected_when_the_category_of_the_previous_flow_is_archived(
    category_repository, session_repository, engine, work_category, clock, scenario_repository
):
    record_flow(session_repository, work_category, clock())
    category_repository.archive(work_category.id)

    home_view_model = make_home_view_model(
        category_repository, session_repository, engine, scenario_repository
    )

    assert home_view_model.selected_category().is_system is True


def test_preselect_picks_up_a_flow_that_was_recorded_since(
    home_view_model, session_repository, work_category, clock
):
    assert home_view_model.selected_category().is_system is True
    record_flow(session_repository, work_category, clock())

    assert home_view_model.selected_category().is_system is True  # not before preselect
    home_view_model.preselect()

    assert home_view_model.selected_category() == work_category


def test_preselect_discards_a_choice_made_since(
    home_view_model, session_repository, work_category, reading_category, clock
):
    record_flow(session_repository, work_category, clock())
    home_view_model.preselect()
    home_view_model.select(reading_category.id)

    home_view_model.preselect()

    assert home_view_model.selected_category() == work_category


# --- choosing and starting ---------------------------------------------------------


def test_a_chosen_category_becomes_the_selected_one(home_view_model, work_category):
    home_view_model.select(work_category.id)

    assert home_view_model.selected_category() == work_category


def test_start_begins_a_flow_with_the_selected_category(
    home_view_model, engine, work_category, clock
):
    home_view_model.select(work_category.id)

    home_view_model.start()

    assert engine.current_interval == RunningInterval(
        kind=IntervalKind.WORK,
        category_id=work_category.id,
        planned_seconds=25 * 60,
        started_at=clock(),
    )


def test_start_without_a_choice_begins_a_flow_with_the_preselected_category(
    category_repository, session_repository, engine, work_category, clock, scenario_repository
):
    record_flow(session_repository, work_category, clock())
    home_view_model = make_home_view_model(
        category_repository, session_repository, engine, scenario_repository
    )

    home_view_model.start()

    assert engine.current_interval.category_id == work_category.id


# --- strings -----------------------------------------------------------------------


@pytest.mark.parametrize("key", ["home.category", "home.start"])
def test_the_strings_of_the_home_screen_exist_in_the_catalog(key):
    assert t(key)


# --- starting a scenario -------------------------------------------------------------


@pytest.fixture
def day(scenario_repository, work_category, reading_category):
    return scenario_repository.create(
        Scenario(
            "Day",
            (ScenarioRow(work_category.id, 2), ScenarioRow(reading_category.id, 1)),
        )
    )


@pytest.fixture
def evening(scenario_repository, work_category):
    return scenario_repository.create(Scenario("Evening", (ScenarioRow(work_category.id, 1),)))


def run_until_the_session_ends(engine, clock):
    for _ in range(50):
        if engine.current_interval is not None:
            clock.advance(engine.remaining_seconds())
            engine.tick()
        elif engine.upcoming_interval is not None:
            engine.confirm()
        else:
            return
    raise AssertionError("the session did not end")


def test_a_flow_is_what_is_started_at_first(home_view_model):
    assert home_view_model.start_kind() == StartKind.FLOW


def test_without_scenarios_none_is_selected_and_a_scenario_cannot_be_chosen(home_view_model):
    home_view_model.select_start_kind(StartKind.SCENARIO)

    assert home_view_model.scenarios() == []
    assert home_view_model.selected_scenario() is None
    assert home_view_model.start_kind() == StartKind.FLOW


def test_the_scenarios_are_listed_by_name(home_view_model, day, evening):
    assert [scenario.name for scenario in home_view_model.scenarios()] == ["Day", "Evening"]


def test_the_first_scenario_is_selected_at_first(home_view_model, day, evening):
    assert home_view_model.selected_scenario() == day


def test_a_scenario_is_selected_by_id(home_view_model, day, evening):
    home_view_model.select_scenario(evening.id)

    assert home_view_model.selected_scenario() == evening


def test_a_scenario_can_be_chosen_to_start(home_view_model, day):
    home_view_model.select_start_kind(StartKind.SCENARIO)

    assert home_view_model.start_kind() == StartKind.SCENARIO


def test_start_runs_the_selected_scenario_when_a_scenario_is_chosen(
    home_view_model, engine, day, evening, work_category
):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.select_scenario(evening.id)

    home_view_model.start()

    assert engine.scenario == evening
    assert engine.current_interval.category_id == work_category.id


def test_start_runs_a_flow_when_a_flow_is_chosen(home_view_model, engine, day, reading_category):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.select_start_kind(StartKind.FLOW)
    home_view_model.select(reading_category.id)

    home_view_model.start()

    assert engine.scenario is None
    assert engine.current_interval.category_id == reading_category.id


def test_the_choice_of_scenario_is_kept_between_sessions(home_view_model, engine, day, evening, clock):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.select_scenario(evening.id)
    home_view_model.start()
    run_until_the_session_ends(engine, clock)

    assert home_view_model.start_kind() == StartKind.SCENARIO
    assert home_view_model.selected_scenario() == evening


def test_a_deleted_scenario_gives_way_to_the_first_one(
    home_view_model, scenario_repository, day, evening
):
    home_view_model.select_scenario(evening.id)

    scenario_repository.delete(evening.id)

    assert home_view_model.selected_scenario() == day


def test_a_flow_is_chosen_again_when_the_last_scenario_is_deleted(
    home_view_model, scenario_repository, day
):
    home_view_model.select_start_kind(StartKind.SCENARIO)

    scenario_repository.delete(day.id)

    assert home_view_model.start_kind() == StartKind.FLOW


# --- the summary ---------------------------------------------------------------------


def test_there_is_no_summary_at_first(home_view_model):
    assert home_view_model.summary_text() is None


def test_a_scenario_that_ran_to_its_end_leaves_a_summary(home_view_model, engine, day, clock):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.start()

    run_until_the_session_ends(engine, clock)

    assert home_view_model.mode() == HomeMode.IDLE
    assert home_view_model.summary_text() == 'Scenario "Day" complete: 3 done, 0 skipped'


def test_a_skipped_work_interval_is_told_in_the_summary(home_view_model, engine, day, clock):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.start()
    engine.skip()  # the first work interval
    run_until_the_session_ends(engine, clock)

    assert home_view_model.summary_text() == 'Scenario "Day" complete: 2 done, 1 skipped'


def test_a_stopped_scenario_leaves_no_summary(home_view_model, engine, day):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.start()

    engine.stop()

    assert home_view_model.summary_text() is None


def test_a_new_session_clears_the_summary(home_view_model, engine, day, clock):
    home_view_model.select_start_kind(StartKind.SCENARIO)
    home_view_model.start()
    run_until_the_session_ends(engine, clock)

    home_view_model.select_start_kind(StartKind.FLOW)
    home_view_model.start()

    assert home_view_model.summary_text() is None

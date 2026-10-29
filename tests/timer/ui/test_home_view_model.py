import pytest
from timer.engine import Engine
from timer.i18n import t
from timer.intervals import IntervalKind, RunningInterval
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.sessions import SessionRepository
from timer.storage.settings import Settings
from timer.ui.home_view_model import HomeMode, HomeViewModel


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


def make_home_view_model(category_repository, session_repository, engine):
    return HomeViewModel(category_repository, session_repository, engine)


@pytest.fixture
def home_view_model(category_repository, session_repository, engine):
    return make_home_view_model(category_repository, session_repository, engine)


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
    category_repository, session_repository, engine, work_category, clock
):
    record_flow(session_repository, work_category, clock())

    home_view_model = make_home_view_model(category_repository, session_repository, engine)

    assert home_view_model.selected_category() == work_category


def test_the_most_recent_flow_decides_the_preselection(
    category_repository, session_repository, engine, work_category, reading_category, clock
):
    record_flow(session_repository, work_category, clock())
    clock.advance(3600)
    record_flow(session_repository, reading_category, clock())

    home_view_model = make_home_view_model(category_repository, session_repository, engine)

    assert home_view_model.selected_category() == reading_category


def test_none_is_preselected_when_the_category_of_the_previous_flow_is_archived(
    category_repository, session_repository, engine, work_category, clock
):
    record_flow(session_repository, work_category, clock())
    category_repository.archive(work_category.id)

    home_view_model = make_home_view_model(category_repository, session_repository, engine)

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
    category_repository, session_repository, engine, work_category, clock
):
    record_flow(session_repository, work_category, clock())
    home_view_model = make_home_view_model(category_repository, session_repository, engine)

    home_view_model.start()

    assert engine.current_interval.category_id == work_category.id


# --- strings -----------------------------------------------------------------------


@pytest.mark.parametrize("key", ["home.category", "home.start"])
def test_the_strings_of_the_home_screen_exist_in_the_catalog(key):
    assert t(key)

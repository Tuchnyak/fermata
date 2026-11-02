import pytest
from timer.engine import Engine
from timer.i18n import t
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.settings import Settings
from timer.ui.running_view_model import RunningViewModel


@pytest.fixture
def category_repository():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return CategoryRepository(db)


@pytest.fixture
def work_category(category_repository):
    return category_repository.create("Work", "#112233")


@pytest.fixture
def engine(clock):
    return Engine(get_settings=Settings, clock=clock)


@pytest.fixture
def running_view_model(engine, category_repository):
    return RunningViewModel(engine, category_repository)


@pytest.fixture
def running_flow(engine, work_category):
    engine.start_flow(work_category.id)


def skip_times(engine, count):
    for _ in range(count):
        engine.skip()


# --- the title ---------------------------------------------------------------


def test_a_work_interval_is_titled_with_its_category_name(
    running_view_model, running_flow
):
    assert running_view_model.title() == "Work"


def test_the_system_category_is_titled_none(running_view_model, engine):
    engine.start_flow(1)

    assert running_view_model.title() == "None"


def test_a_short_break_is_titled_short_break(running_view_model, running_flow, engine):
    engine.skip()

    assert running_view_model.title() == "SHORT BREAK"


def test_a_long_break_is_titled_long_break(running_view_model, running_flow, engine):
    skip_times(engine, 7)  # four work intervals and three short breaks

    assert running_view_model.title() == "LONG BREAK"


# --- the color --------------------------------------------------------------


def test_a_work_interval_shows_the_color_of_its_category(
    running_view_model, running_flow
):
    assert running_view_model.color() == "#112233"


def test_the_system_category_shows_its_own_color(
    running_view_model, engine, category_repository
):
    engine.start_flow(1)

    assert running_view_model.color() == category_repository.get_by_id(1).color


def test_a_break_has_no_color(running_view_model, running_flow, engine):
    engine.skip()

    assert running_view_model.color() is None


# --- the work interval number --------------------------------------------------


def test_the_first_work_interval_is_number_one(running_view_model, running_flow):
    assert running_view_model.work_interval_number() == 1


def test_a_break_carries_the_number_of_the_work_interval_before_it(
    running_view_model, running_flow, engine
):
    engine.skip()

    assert running_view_model.work_interval_number() == 1


def test_each_work_interval_is_numbered_after_the_previous_one_skipped_or_not(
    running_view_model, running_flow, engine
):
    skip_times(engine, 2)  # the first work interval and its break

    assert running_view_model.work_interval_number() == 2

    skip_times(engine, 2)

    assert running_view_model.work_interval_number() == 3


# --- the countdown -------------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "shown"),
    [
        (0, "25:00"),
        (1, "24:59"),
        (0.4, "25:00"),  # a started second still counts: it is rounded up
        (90.5, "23:30"),
        (25 * 60 - 0.4, "00:01"),
        (25 * 60, "00:00"),
    ],
)
def test_the_countdown_shows_the_remaining_time_rounded_up_to_a_second(
    running_view_model, running_flow, clock, elapsed, shown
):
    clock.advance(elapsed)

    assert running_view_model.countdown() == shown


def test_the_countdown_of_a_break_shows_the_length_of_the_break(
    running_view_model, running_flow, engine
):
    engine.skip()

    assert running_view_model.countdown() == "05:00"


def test_the_countdown_stands_still_while_paused(
    running_view_model, running_flow, clock
):
    clock.advance(60)
    running_view_model.toggle_pause()

    clock.advance(600)

    assert running_view_model.countdown() == "24:00"


# --- the buttons ---------------------------------------------------------------


def test_the_pause_button_says_pause_and_then_resume(running_view_model, running_flow):
    assert running_view_model.pause_button_text() == t("running.pause")

    running_view_model.toggle_pause()
    assert running_view_model.pause_button_text() == t("running.resume")

    running_view_model.toggle_pause()
    assert running_view_model.pause_button_text() == t("running.pause")


def test_toggle_pause_pauses_and_resumes_the_engine(
    running_view_model, running_flow, engine
):
    running_view_model.toggle_pause()
    assert engine.is_paused is True

    running_view_model.toggle_pause()
    assert engine.is_paused is False


def test_skip_moves_the_engine_to_the_next_interval(
    running_view_model, running_flow, engine
):
    running_view_model.skip()

    assert engine.current_interval.kind == "short_break"


def test_stop_ends_the_flow(running_view_model, running_flow, engine):
    running_view_model.stop()

    assert engine.current_interval is None


def test_tick_lets_the_engine_notice_that_the_time_is_up(
    running_view_model, running_flow, engine, clock
):
    clock.advance(25 * 60)

    running_view_model.tick()

    assert engine.current_interval is None


# --- strings -------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "running.short_break",
        "running.long_break",
        "running.pause",
        "running.resume",
        "running.skip",
        "running.stop",
        "running.stop_confirm",
    ],
)
def test_the_strings_of_the_running_screen_exist_in_the_catalog(key):
    assert t(key)


def test_the_label_of_the_work_interval_number_shows_the_number():
    assert "3" in t("running.work_interval_number", number=3)

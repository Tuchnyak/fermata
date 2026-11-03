import pytest
from timer.engine import Engine
from timer.storage.settings import Settings
from timer.ui.fullscreen import Fullscreen
from timer.ui.hotkeys import HotkeyAction, HotkeyHandler, action_for_key
from timer.ui.navigation import Navigation, Screen

CATEGORY_ID = 7


@pytest.fixture
def engine(clock):
    return Engine(get_settings=Settings, clock=clock)  # the default settings


@pytest.fixture
def navigation():
    return Navigation()


@pytest.fixture
def start_requests():
    return []


@pytest.fixture
def fullscreen():
    return Fullscreen()


@pytest.fixture
def handler(engine, navigation, start_requests, fullscreen):
    return HotkeyHandler(
        engine,
        navigation,
        start_flow=lambda: start_requests.append("start"),
        fullscreen=fullscreen,
    )


def press(handler, key, text_field_focused=False):
    handler.handle_key(key, text_field_focused=text_field_focused)


def make_the_engine_wait(engine, clock):
    engine.start_flow(CATEGORY_ID)
    clock.advance(engine.remaining_seconds())
    engine.tick()


# --- the key mapping ---------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("space", HotkeyAction.TOGGLE_PAUSE),
        ("Return", HotkeyAction.CONFIRM),
        ("KP_Enter", HotkeyAction.CONFIRM),
        ("Escape", HotkeyAction.BACK),
        ("F11", HotkeyAction.TOGGLE_FULLSCREEN),
    ],
)
def test_keys_are_mapped_to_actions(key, expected):
    assert action_for_key(key, text_field_focused=False) == expected


@pytest.mark.parametrize("key", ["a", "1", "Tab", "BackSpace", "Shift_L", "F10"])
def test_other_keys_have_no_action(key):
    assert action_for_key(key, text_field_focused=False) is None


@pytest.mark.parametrize("key", ["space", "Return", "KP_Enter", "Escape"])
def test_no_key_has_an_action_while_a_text_field_has_focus(key):
    assert action_for_key(key, text_field_focused=True) is None


# --- Space -------------------------------------------------------------------


def test_space_on_the_home_screen_asks_to_start_a_flow_when_idle(
    handler, engine, start_requests
):
    press(handler, "space")

    assert start_requests == ["start"]
    assert engine.current_interval is None  # starting is up to the home screen


def test_space_does_not_start_a_flow_from_a_secondary_screen(
    handler, navigation, start_requests
):
    navigation.open(Screen.CATEGORIES)

    press(handler, "space")

    assert start_requests == []


def test_space_pauses_a_running_interval_and_resumes_a_paused_one(handler, engine):
    engine.start_flow(CATEGORY_ID)

    press(handler, "space")
    assert engine.is_paused is True

    press(handler, "space")
    assert engine.is_paused is False


def test_space_pauses_a_running_interval_from_a_secondary_screen_too(
    handler, engine, navigation
):
    engine.start_flow(CATEGORY_ID)
    navigation.open(Screen.SETTINGS)

    press(handler, "space")

    assert engine.is_paused is True


def test_space_does_nothing_while_the_engine_waits_for_confirmation(
    handler, engine, clock, start_requests
):
    make_the_engine_wait(engine, clock)

    press(handler, "space")

    assert engine.upcoming_interval is not None
    assert engine.current_interval is None
    assert engine.is_paused is False
    assert start_requests == []


# --- Enter -------------------------------------------------------------------


def test_enter_starts_the_upcoming_interval_when_waiting(handler, engine, clock):
    make_the_engine_wait(engine, clock)

    press(handler, "Return")

    assert engine.current_interval is not None
    assert engine.upcoming_interval is None


def test_the_numeric_keypad_enter_confirms_too(handler, engine, clock):
    make_the_engine_wait(engine, clock)

    press(handler, "KP_Enter")

    assert engine.current_interval is not None


def test_enter_does_nothing_while_an_interval_runs_or_when_idle(handler, engine):
    press(handler, "Return")
    assert engine.current_interval is None

    engine.start_flow(CATEGORY_ID)
    started_interval = engine.current_interval
    press(handler, "Return")

    assert engine.current_interval == started_interval


# --- Escape ------------------------------------------------------------------


@pytest.mark.parametrize("screen", [Screen.CATEGORIES, Screen.SETTINGS])
def test_escape_goes_back_from_a_secondary_screen(handler, navigation, screen):
    navigation.open(screen)

    press(handler, "Escape")

    assert navigation.current == Screen.HOME


def test_escape_on_the_home_screen_does_nothing(handler, navigation):
    press(handler, "Escape")

    assert navigation.current == Screen.HOME


# --- text fields and other keys ---------------------------------------------


def test_space_in_a_text_field_does_not_pause_the_timer(handler, engine):
    engine.start_flow(CATEGORY_ID)

    press(handler, "space", text_field_focused=True)

    assert engine.is_paused is False


def test_space_in_a_text_field_does_not_start_a_flow(handler, start_requests):
    press(handler, "space", text_field_focused=True)

    assert start_requests == []


def test_enter_in_a_text_field_does_not_confirm(handler, engine, clock):
    make_the_engine_wait(engine, clock)

    press(handler, "Return", text_field_focused=True)

    assert engine.current_interval is None


def test_escape_in_a_text_field_does_not_go_back(handler, navigation):
    navigation.open(Screen.CATEGORIES)

    press(handler, "Escape", text_field_focused=True)

    assert navigation.current == Screen.CATEGORIES


def test_other_keys_change_nothing(handler, engine, navigation, start_requests):
    engine.start_flow(CATEGORY_ID)
    navigation.open(Screen.SETTINGS)

    press(handler, "a")

    assert engine.is_paused is False
    assert navigation.current == Screen.SETTINGS
    assert start_requests == []


# --- fullscreen --------------------------------------------------------------------


def test_f11_works_also_while_a_text_field_has_focus():
    assert (
        action_for_key("F11", text_field_focused=True) == HotkeyAction.TOGGLE_FULLSCREEN
    )


def test_f11_toggles_fullscreen(handler, fullscreen):
    press(handler, "F11")

    assert fullscreen.is_on is True

    press(handler, "F11")

    assert fullscreen.is_on is False


def test_f11_toggles_fullscreen_while_typing(handler, fullscreen):
    press(handler, "F11", text_field_focused=True)

    assert fullscreen.is_on is True


def test_escape_leaves_fullscreen_first_and_does_not_go_back(handler, fullscreen, navigation):
    navigation.open(Screen.SETTINGS)
    fullscreen.toggle()

    press(handler, "Escape")

    assert fullscreen.is_on is False
    assert navigation.current == Screen.SETTINGS


def test_the_next_escape_goes_back(handler, fullscreen, navigation):
    navigation.open(Screen.SETTINGS)
    fullscreen.toggle()
    press(handler, "Escape")

    press(handler, "Escape")

    assert navigation.current == Screen.HOME


def test_escape_on_the_home_screen_in_fullscreen_only_leaves_fullscreen(handler, fullscreen):
    fullscreen.toggle()

    press(handler, "Escape")

    assert fullscreen.is_on is False


def test_escape_without_fullscreen_still_goes_back(handler, navigation):
    navigation.open(Screen.CATEGORIES)

    press(handler, "Escape")

    assert navigation.current == Screen.HOME


def test_escape_is_still_ignored_while_typing_in_fullscreen(handler, fullscreen):
    fullscreen.toggle()

    press(handler, "Escape", text_field_focused=True)

    assert fullscreen.is_on is True


def test_pause_and_confirm_keep_working_in_fullscreen(handler, fullscreen, engine, clock):
    fullscreen.toggle()
    engine.start_flow(CATEGORY_ID)

    press(handler, "space")

    assert engine.is_paused is True

    press(handler, "space")
    clock.advance(engine.remaining_seconds())
    engine.tick()
    press(handler, "Return")

    assert engine.current_interval is not None

import pytest
from timer.ui.fullscreen import Fullscreen, shows_board
from timer.ui.navigation import Screen


def test_the_window_is_not_fullscreen_at_first():
    assert Fullscreen().is_on is False


def test_toggle_turns_fullscreen_on_and_off():
    fullscreen = Fullscreen()

    fullscreen.toggle()

    assert fullscreen.is_on is True

    fullscreen.toggle()

    assert fullscreen.is_on is False


def test_leave_turns_fullscreen_off():
    fullscreen = Fullscreen()
    fullscreen.toggle()

    fullscreen.leave()

    assert fullscreen.is_on is False


def test_leave_while_not_fullscreen_changes_nothing():
    fullscreen = Fullscreen()

    fullscreen.leave()

    assert fullscreen.is_on is False


def test_the_home_screen_in_fullscreen_is_the_board():
    fullscreen = Fullscreen()
    fullscreen.toggle()

    assert shows_board(fullscreen, Screen.HOME) is True


@pytest.mark.parametrize("screen", [Screen.SCENARIOS, Screen.CATEGORIES, Screen.SETTINGS])
def test_a_secondary_screen_in_fullscreen_looks_as_usual(screen):
    fullscreen = Fullscreen()
    fullscreen.toggle()

    assert shows_board(fullscreen, screen) is False


def test_the_home_screen_in_a_normal_window_is_not_the_board():
    assert shows_board(Fullscreen(), Screen.HOME) is False

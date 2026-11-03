import pytest
from timer.i18n import t
from timer.ui.navigation import Navigation, Screen

SECONDARY_SCREENS = [Screen.SCENARIOS, Screen.CATEGORIES, Screen.HISTORY, Screen.SETTINGS]


def test_the_home_screen_is_shown_first():
    navigation = Navigation()

    assert navigation.current == Screen.HOME
    assert navigation.can_go_back is False


@pytest.mark.parametrize("screen", SECONDARY_SCREENS)
def test_opening_a_secondary_screen_shows_it_and_allows_going_back(screen):
    navigation = Navigation()

    navigation.open(screen)

    assert navigation.current == screen
    assert navigation.can_go_back is True


@pytest.mark.parametrize("screen", SECONDARY_SCREENS)
def test_back_returns_to_the_home_screen(screen):
    navigation = Navigation()
    navigation.open(screen)

    navigation.back()

    assert navigation.current == Screen.HOME
    assert navigation.can_go_back is False


def test_back_on_the_home_screen_does_nothing():
    navigation = Navigation()

    navigation.back()

    assert navigation.current == Screen.HOME


def test_back_from_a_secondary_screen_opened_from_another_one_leads_home():
    navigation = Navigation()
    navigation.open(Screen.CATEGORIES)
    navigation.open(Screen.SETTINGS)

    navigation.back()

    assert navigation.current == Screen.HOME


@pytest.mark.parametrize("screen", list(Screen))
def test_every_screen_has_a_title_in_the_catalog(screen):
    assert t(f"screen.{screen.value}")


def test_the_back_button_has_a_label_in_the_catalog():
    assert t("nav.back")

import sys

import pytest
from fermata.i18n import t
from fermata.ui.main_window import NAVIGATION_BAR_SCREENS, window_title
from fermata.ui.navigation import Screen


def test_a_release_window_is_titled_fermata(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert window_title() == "Fermata"


def test_a_window_run_from_source_is_marked_as_dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert window_title() == "Fermata (dev)"


def test_a_sped_up_window_shows_the_speed(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert window_title(speed=2) == "Fermata (dev, ×2)"


def test_a_window_at_the_normal_speed_shows_no_speed(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert window_title(speed=1) == "Fermata (dev)"


def test_a_release_window_shows_no_speed(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert window_title(speed=2) == "Fermata"


@pytest.mark.parametrize("key", ["app.title", "app.title_dev", "app.title_dev_speed"])
def test_the_titles_exist_in_the_catalog(key):
    assert t(key, speed=2)


def test_the_navigation_bar_leads_to_every_secondary_screen_in_this_order():
    assert NAVIGATION_BAR_SCREENS == (
        Screen.SCENARIOS,
        Screen.CATEGORIES,
        Screen.HISTORY,
        Screen.SETTINGS,
    )

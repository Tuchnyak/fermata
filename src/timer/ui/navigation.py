"""Which screen the main window shows.

The window has one home screen (the timer) and secondary screens that open inside it. There
is no history: going back from any secondary screen leads to the home screen.
"""

from enum import StrEnum


class Screen(StrEnum):
    HOME = "home"
    SCENARIOS = "scenarios"
    CATEGORIES = "categories"
    SETTINGS = "settings"
    HISTORY = "history"


class Navigation:
    def __init__(self):
        self._current = Screen.HOME

    @property
    def current(self) -> Screen:
        return self._current

    @property
    def can_go_back(self) -> bool:
        return self._current != Screen.HOME

    def open(self, screen: Screen) -> None:
        self._current = screen

    def back(self) -> None:
        self._current = Screen.HOME

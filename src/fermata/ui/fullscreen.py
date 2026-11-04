"""Whether the window is fullscreen, and what that makes the home screen: a board (spec section 11).

Fullscreen is never remembered: the application always starts in a normal window.
"""

from fermata.ui.navigation import Screen


class Fullscreen:
    def __init__(self):
        self._is_on = False

    @property
    def is_on(self) -> bool:
        return self._is_on

    def toggle(self) -> None:
        self._is_on = not self._is_on

    def leave(self) -> None:
        self._is_on = False


def shows_board(fullscreen: Fullscreen, screen: Screen) -> bool:
    """The board (the interval, the countdown and the progress, no header and no buttons) is the
    home screen in fullscreen; a secondary screen looks as usual."""
    return fullscreen.is_on and screen == Screen.HOME

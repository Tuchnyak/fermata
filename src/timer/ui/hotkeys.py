"""Hotkeys: which key does what, and the handler that carries the action out.

The key names are Tk keysyms, but nothing here imports Tk, so it is tested without a display.
All keys are ignored while a text field has focus, so typing in a field never acts on the
timer.
"""

from collections.abc import Callable
from enum import Enum, auto

from timer.engine import Engine
from timer.ui.navigation import Navigation, Screen


class HotkeyAction(Enum):
    TOGGLE_PAUSE = auto()
    CONFIRM = auto()
    BACK = auto()


_ACTIONS_BY_KEY = {
    "space": HotkeyAction.TOGGLE_PAUSE,
    "Return": HotkeyAction.CONFIRM,
    "KP_Enter": HotkeyAction.CONFIRM,
    "Escape": HotkeyAction.BACK,
}


def action_for_key(key: str, *, text_field_focused: bool) -> HotkeyAction | None:
    if text_field_focused:
        return None
    return _ACTIONS_BY_KEY.get(key)


class HotkeyHandler:
    def __init__(
        self, engine: Engine, navigation: Navigation, start_flow: Callable[[], None]
    ):
        self._engine = engine
        self._navigation = navigation
        self._start_flow = start_flow

    def handle_key(self, key: str, *, text_field_focused: bool) -> None:
        action = action_for_key(key, text_field_focused=text_field_focused)
        if action == HotkeyAction.TOGGLE_PAUSE:
            self._toggle_pause()
        elif action == HotkeyAction.CONFIRM:
            self._engine.confirm()
        elif action == HotkeyAction.BACK:
            self._navigation.back()

    def _toggle_pause(self) -> None:
        if self._engine.current_interval is not None:
            if self._engine.is_paused:
                self._engine.resume()
            else:
                self._engine.pause()
            return
        is_waiting = self._engine.upcoming_interval is not None
        # A flow is started from the home screen only: that is where the category is chosen.
        if not is_waiting and self._navigation.current == Screen.HOME:
            self._start_flow()

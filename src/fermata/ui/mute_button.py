"""The button that switches all the sounds off and on: in the header of the home screen, on the
fullscreen board in the corner."""

import tkinter

import ttkbootstrap as ttk
from fermata.i18n import t
from fermata.ui.settings_view_model import SettingsViewModel


class MuteButton(ttk.Button):
    def __init__(self, parent: tkinter.Misc, view_model: SettingsViewModel):
        # It does not take focus: Space on a focused button would press it as well as act as a
        # hotkey.
        super().__init__(parent, command=self._toggle, takefocus=False)
        self._view_model = view_model
        self._show(view_model.settings().sound)

    def _toggle(self) -> None:
        self._show(self._view_model.toggle_sound())

    def _show(self, sound_is_on: bool) -> None:
        self.configure(text=t("home.sound_on" if sound_is_on else "home.sound_off"))

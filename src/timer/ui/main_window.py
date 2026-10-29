"""The main window: a header (navigation) above the content of the current screen.

Only the screens' placeholders exist so far; the real screens replace them piece by piece.
"""

import tkinter
from functools import partial

import ttkbootstrap as ttk
from timer.build import is_release
from timer.i18n import t
from timer.ui.categories_screen import CategoriesScreen
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.navigation import Navigation, Screen
from timer.ui.settings_screen import SettingsScreen
from timer.ui.settings_view_model import SettingsViewModel

NAVIGATION_BAR_SCREENS = (Screen.CATEGORIES, Screen.SETTINGS)


def window_title() -> str:
    return t("app.title") if is_release() else t("app.title_dev")


class MainWindow:
    def __init__(
        self,
        root: ttk.Window,
        navigation: Navigation,
        hotkey_handler: HotkeyHandler,
        categories_view_model: CategoriesViewModel,
        settings_view_model: SettingsViewModel,
    ):
        self._root = root
        self._navigation = navigation
        self._hotkey_handler = hotkey_handler
        self._categories_view_model = categories_view_model
        self._settings_view_model = settings_view_model
        root.title(window_title())
        root.geometry("720x600")
        self._header = ttk.Frame(root, padding=8)
        self._header.pack(fill="x")
        self._content = ttk.Frame(root, padding=8)
        self._content.pack(fill="both", expand=True)
        root.bind("<Key>", self._on_key)
        self._show_current_screen()

    def _on_key(self, event: tkinter.Event) -> None:
        screen_before = self._navigation.current
        self._hotkey_handler.handle_key(
            event.keysym, text_field_focused=self._text_field_has_focus()
        )
        if self._navigation.current != screen_before:
            self._show_current_screen()

    def _text_field_has_focus(self) -> bool:
        return isinstance(self._root.focus_get(), (tkinter.Entry, tkinter.Text))

    def _open(self, screen: Screen) -> None:
        self._navigation.open(screen)
        self._show_current_screen()

    def _go_back(self) -> None:
        self._navigation.back()
        self._show_current_screen()

    def _show_current_screen(self) -> None:
        for frame in (self._header, self._content):
            for child in frame.winfo_children():
                child.destroy()

        title = t(f"screen.{self._navigation.current}")
        if self._navigation.can_go_back:
            ttk.Button(
                self._header, text=t("nav.back"), command=self._go_back, takefocus=False
            ).pack(side="left")
            ttk.Label(self._header, text=title, font=("TkDefaultFont", 14)).pack(
                side="left", padx=16
            )
            actions = ttk.Frame(self._header)
            actions.pack(side="right")
        else:
            for screen in NAVIGATION_BAR_SCREENS:
                ttk.Button(
                    self._header,
                    text=t(f"screen.{screen}"),
                    command=partial(self._open, screen),
                    takefocus=False,
                ).pack(side="left", padx=(0, 8))

        if self._navigation.current == Screen.CATEGORIES:
            CategoriesScreen(self._content, self._categories_view_model).pack(
                fill="both", expand=True
            )
        elif self._navigation.current == Screen.SETTINGS:
            SettingsScreen(self._content, self._settings_view_model, actions).pack(
                fill="both", expand=True
            )
        else:
            ttk.Label(self._content, text=title, font=("TkDefaultFont", 24)).pack(
                expand=True
            )

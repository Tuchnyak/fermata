"""The main window: a header (navigation) above the content of the current screen.

Only the screens' placeholders exist so far; the real screens replace them piece by piece.
"""

import tkinter
from functools import partial
from tkinter import ttk as tk_ttk

import ttkbootstrap as ttk
from timer.build import is_release
from timer.i18n import t
from timer.ui.categories_screen import CategoriesScreen
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.home_view_model import HomeMode, HomeViewModel
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.navigation import Navigation, Screen
from timer.ui.running_panel import RunningPanel
from timer.ui.running_view_model import RunningViewModel
from timer.ui.scenarios_screen import ScenariosScreen
from timer.ui.scenarios_view_model import ScenariosViewModel
from timer.ui.settings_screen import SettingsScreen
from timer.ui.settings_view_model import SettingsViewModel
from timer.ui.start_panel import StartPanel
from timer.ui.waiting_panel import WaitingPanel
from timer.ui.waiting_view_model import WaitingViewModel

NAVIGATION_BAR_SCREENS = (Screen.SCENARIOS, Screen.CATEGORIES, Screen.SETTINGS)
TICK_MILLISECONDS = 200  # how often the engine is ticked and the countdown redrawn


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
        home_view_model: HomeViewModel,
        running_view_model: RunningViewModel,
        waiting_view_model: WaitingViewModel,
        scenarios_view_model: ScenariosViewModel,
    ):
        self._root = root
        self._navigation = navigation
        self._hotkey_handler = hotkey_handler
        self._categories_view_model = categories_view_model
        self._settings_view_model = settings_view_model
        self._home_view_model = home_view_model
        self._running_view_model = running_view_model
        self._waiting_view_model = waiting_view_model
        self._scenarios_view_model = scenarios_view_model
        self._shown_home_mode: HomeMode | None = None
        self._running_panel: RunningPanel | None = None
        root.title(window_title())
        root.geometry("720x680")
        self._header = ttk.Frame(root, padding=8)
        self._header.pack(fill="x")
        self._content = ttk.Frame(root, padding=8)
        self._content.pack(fill="both", expand=True)
        root.bind("<Key>", self._on_key)
        self._show_current_screen()
        root.after(TICK_MILLISECONDS, self._on_tick)

    def _on_tick(self) -> None:
        # The engine is ticked whatever screen is shown, so that intervals end on time.
        self._running_view_model.tick()
        self._refresh_home_screen()
        self._root.after(TICK_MILLISECONDS, self._on_tick)

    def _refresh_home_screen(self) -> None:
        """Redraw the home screen if the engine has changed state, or update the countdown."""
        if self._navigation.current != Screen.HOME:
            return
        if self._home_view_model.mode() != self._shown_home_mode:
            self._show_current_screen()
        elif self._running_panel is not None:
            self._running_panel.refresh()

    def _on_key(self, event: tkinter.Event) -> None:
        screen_before = self._navigation.current
        self._hotkey_handler.handle_key(
            event.keysym, text_field_focused=self._text_field_has_focus()
        )
        if self._navigation.current != screen_before:
            self._show_current_screen()
        else:
            self._refresh_home_screen()

    def _text_field_has_focus(self) -> bool:
        try:
            widget = self._root.focus_get()
        except KeyError:  # the focus is in the drop-down list of a combo box
            return False
        if isinstance(widget, tk_ttk.Combobox) and str(widget.cget("state")) == "readonly":
            return False  # a list to choose from, nothing is typed into it
        return isinstance(widget, (tkinter.Entry, tkinter.Text))

    def _open(self, screen: Screen) -> None:
        self._navigation.open(screen)
        self._show_current_screen()

    def _go_back(self) -> None:
        self._navigation.back()
        self._show_current_screen()

    def _show_current_screen(self) -> None:
        self._shown_home_mode = None
        self._running_panel = None
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

        if self._navigation.current == Screen.SCENARIOS:
            ScenariosScreen(
                self._content, self._scenarios_view_model, actions, self._go_back
            ).pack(fill="both", expand=True)
        elif self._navigation.current == Screen.CATEGORIES:
            CategoriesScreen(self._content, self._categories_view_model).pack(
                fill="both", expand=True
            )
        elif self._navigation.current == Screen.SETTINGS:
            SettingsScreen(self._content, self._settings_view_model, actions).pack(
                fill="both", expand=True
            )
        else:
            self._show_home_content()

    def _show_home_content(self) -> None:
        self._shown_home_mode = self._home_view_model.mode()
        if self._shown_home_mode == HomeMode.RUNNING:
            self._running_panel = RunningPanel(self._content, self._running_view_model)
            self._running_panel.pack(fill="both", expand=True)
        elif self._shown_home_mode == HomeMode.WAITING:
            WaitingPanel(self._content, self._waiting_view_model).pack(
                fill="both", expand=True
            )
        else:
            StartPanel(self._content, self._home_view_model).pack(
                fill="both", expand=True
            )

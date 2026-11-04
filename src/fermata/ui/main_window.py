"""The main window: a header (navigation) above the content of the current screen.

Only the screens' placeholders exist so far; the real screens replace them piece by piece.
"""

import tkinter
from functools import partial
from tkinter import ttk as tk_ttk

import ttkbootstrap as ttk
from fermata.background_sound import BackgroundSound
from fermata.build import is_release
from fermata.i18n import current_language, t
from fermata.ui.categories_screen import CategoriesScreen
from fermata.ui.categories_view_model import CategoriesViewModel
from fermata.ui.history_screen import HistoryScreen
from fermata.ui.library_locale import apply_library_locale
from fermata.ui.history_view_model import HistoryViewModel
from fermata.ui.home_view_model import HomeMode, HomeViewModel
from fermata.ui.fullscreen import Fullscreen, shows_board
from fermata.ui.hotkeys import HotkeyHandler
from fermata.ui.mute_button import MuteButton
from fermata.ui.navigation import Navigation, Screen
from fermata.ui.running_panel import RunningPanel
from fermata.ui.running_view_model import RunningViewModel
from fermata.ui.scenarios_screen import ScenariosScreen
from fermata.ui.scenarios_view_model import ScenariosViewModel
from fermata.ui.settings_screen import SettingsScreen
from fermata.ui.settings_view_model import SettingsViewModel
from fermata.ui.start_panel import StartPanel
from fermata.ui.waiting_panel import WaitingPanel
from fermata.ui.waiting_view_model import WaitingViewModel
from fermata.window_geometry import MIN_SIZE, placement_offset, startup_geometry, without_offset

NAVIGATION_BAR_SCREENS = (Screen.SCENARIOS, Screen.CATEGORIES, Screen.HISTORY, Screen.SETTINGS)
TICK_MILLISECONDS = 200  # how often the engine is ticked and the countdown redrawn
PLACEMENT_MILLISECONDS = 300  # by then the window manager has placed the window


def window_title(speed: int = 1) -> str:
    """"Timer"; a run from source says so, and what speed its clock goes at if not the normal."""
    if is_release():
        return t("app.title")
    if speed != 1:
        return t("app.title_dev_speed", speed=speed)
    return t("app.title_dev")


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
        history_view_model: HistoryViewModel,
        fullscreen: Fullscreen,
        background_sound: BackgroundSound,
        speed: int = 1,
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
        self._history_view_model = history_view_model
        self._fullscreen = fullscreen
        self._background_sound = background_sound
        self._speed = speed
        self._settings_draft: dict[str, object] | None = None
        self._shown_home_mode: HomeMode | None = None
        self._running_panel: RunningPanel | None = None
        self._normal_geometry = ""  # of the normal window, taken when it goes fullscreen
        self._placement_offset = (0, 0)
        root.title(window_title(speed))
        self._asked_geometry = startup_geometry(
            settings_view_model.settings().window_geometry,
            root.winfo_screenwidth(),
            root.winfo_screenheight(),
        )
        root.geometry(self._asked_geometry)
        root.minsize(*MIN_SIZE)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._header = ttk.Frame(root, padding=8)
        self._header.pack(fill="x")
        self._content = ttk.Frame(root, padding=8)
        self._content.pack(fill="both", expand=True)
        root.bind("<Key>", self._on_key)
        self._show_current_screen()
        root.after(TICK_MILLISECONDS, self._on_tick)
        root.after(PLACEMENT_MILLISECONDS, self._measure_placement)

    def _measure_placement(self) -> None:
        if not self._fullscreen.is_on:
            self._placement_offset = placement_offset(
                self._asked_geometry, self._root.geometry()
            )

    def _on_tick(self) -> None:
        # The engine is ticked whatever screen is shown, so that intervals end on time.
        self._running_view_model.tick()
        self._background_sound.update()
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
        fullscreen_before = self._fullscreen.is_on
        self._hotkey_handler.handle_key(
            event.keysym, text_field_focused=self._text_field_has_focus()
        )
        if self._fullscreen.is_on != fullscreen_before:
            self._apply_fullscreen()
        elif self._navigation.current != screen_before:
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

    def _toggle_fullscreen(self) -> None:
        self._fullscreen.toggle()
        self._apply_fullscreen()

    def _apply_fullscreen(self) -> None:
        if self._fullscreen.is_on:
            self._normal_geometry = self._root.geometry()
        self._root.attributes("-fullscreen", self._fullscreen.is_on)
        self._show_current_screen()

    def _on_close(self) -> None:
        # Fullscreen is never remembered: a window closed in it keeps its normal geometry.
        geometry = self._normal_geometry if self._fullscreen.is_on else self._root.geometry()
        self._settings_view_model.remember_window_geometry(
            without_offset(geometry, self._placement_offset)
        )
        self._background_sound.stop()
        self._root.destroy()

    def _on_language_changed(self, draft: dict[str, object]) -> None:
        """Draw everything again in the new language; the settings form keeps its draft."""
        apply_library_locale(current_language())
        self._root.title(window_title(self._speed))
        self._settings_draft = draft
        self._show_current_screen()

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

        board = shows_board(self._fullscreen, self._navigation.current)
        if board:
            self._header.pack_forget()
        elif not self._header.winfo_ismapped():
            self._header.pack(fill="x", before=self._content)

        title = t(f"screen.{self._navigation.current}")
        if board:
            actions = None
        elif self._navigation.can_go_back:
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
            ttk.Button(
                self._header,
                text=t("nav.fullscreen"),
                command=self._toggle_fullscreen,
                takefocus=False,
            ).pack(side="right")
            MuteButton(self._header, self._settings_view_model).pack(
                side="right", padx=(0, 8)
            )

        if self._navigation.current == Screen.SCENARIOS:
            ScenariosScreen(
                self._content, self._scenarios_view_model, actions, self._go_back
            ).pack(fill="both", expand=True)
        elif self._navigation.current == Screen.CATEGORIES:
            CategoriesScreen(self._content, self._categories_view_model).pack(
                fill="both", expand=True
            )
        elif self._navigation.current == Screen.HISTORY:
            HistoryScreen(self._content, self._history_view_model).pack(
                fill="both", expand=True
            )
        elif self._navigation.current == Screen.SETTINGS:
            draft, self._settings_draft = self._settings_draft, None
            SettingsScreen(
                self._content,
                self._settings_view_model,
                actions,
                self._on_language_changed,
                draft,
            ).pack(fill="both", expand=True)
        else:
            self._show_home_content(board)

    def _show_home_content(self, board: bool) -> None:
        self._shown_home_mode = self._home_view_model.mode()
        self._show_home_panel(board)
        if board:
            # The board has no header; its one button is over the corner of the panel.
            MuteButton(self._content, self._settings_view_model).place(
                relx=1.0, rely=0.0, anchor="ne"
            )

    def _show_home_panel(self, board: bool) -> None:
        if self._shown_home_mode == HomeMode.RUNNING:
            self._running_panel = RunningPanel(
                self._content, self._running_view_model, board
            )
            self._running_panel.pack(fill="both", expand=True)
        elif self._shown_home_mode == HomeMode.WAITING:
            WaitingPanel(self._content, self._waiting_view_model, board).pack(
                fill="both", expand=True
            )
        else:
            StartPanel(self._content, self._home_view_model).pack(
                fill="both", expand=True
            )

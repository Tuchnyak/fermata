"""The main window: a header (navigation) above the content of the current screen.

Only the screens' placeholders exist so far; the real screens replace them piece by piece.
"""

import tkinter
from functools import partial

import ttkbootstrap as ttk
from timer.build import is_release
from timer.i18n import t
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.navigation import Navigation, Screen

NAVIGATION_BAR_SCREENS = (Screen.CATEGORIES, Screen.SETTINGS)


def window_title() -> str:
    return t("app.title") if is_release() else t("app.title_dev")


class MainWindow:
    def __init__(
        self, root: ttk.Window, navigation: Navigation, hotkey_handler: HotkeyHandler
    ):
        self._root = root
        self._navigation = navigation
        self._hotkey_handler = hotkey_handler
        root.title(window_title())
        root.geometry("640x420")
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
        else:
            for screen in NAVIGATION_BAR_SCREENS:
                ttk.Button(
                    self._header,
                    text=t(f"screen.{screen}"),
                    command=partial(self._open, screen),
                    takefocus=False,
                ).pack(side="left", padx=(0, 8))

        ttk.Label(self._content, text=title, font=("TkDefaultFont", 24)).pack(expand=True)

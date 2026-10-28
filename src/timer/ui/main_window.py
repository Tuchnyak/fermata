"""The main window: a header (navigation) above the content of the current screen.

Only the screens' placeholders exist so far; the real screens replace them piece by piece.
"""

from functools import partial

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.navigation import Navigation, Screen

NAVIGATION_BAR_SCREENS = (Screen.CATEGORIES, Screen.SETTINGS)


class MainWindow:
    def __init__(self, root: ttk.Window):
        self._navigation = Navigation()
        root.title(t("app.title"))
        root.geometry("640x420")
        self._header = ttk.Frame(root, padding=8)
        self._header.pack(fill="x")
        self._content = ttk.Frame(root, padding=8)
        self._content.pack(fill="both", expand=True)
        self._show_current_screen()

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
            ttk.Button(self._header, text=t("nav.back"), command=self._go_back).pack(
                side="left"
            )
            ttk.Label(self._header, text=title, font=("TkDefaultFont", 14)).pack(
                side="left", padx=16
            )
        else:
            for screen in NAVIGATION_BAR_SCREENS:
                ttk.Button(
                    self._header,
                    text=t(f"screen.{screen}"),
                    command=partial(self._open, screen),
                ).pack(side="left", padx=(0, 8))

        ttk.Label(self._content, text=title, font=("TkDefaultFont", 24)).pack(expand=True)

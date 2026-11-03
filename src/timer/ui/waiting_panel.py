"""The home screen while the engine waits for confirmation: what comes next and the buttons."""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.scale_watcher import ScaleWatcher
from timer.ui.scaling import sizes_for
from timer.ui.waiting_view_model import WaitingViewModel
from ttkbootstrap.dialogs import Messagebox


class WaitingPanel(ttk.Frame):
    def __init__(
        self, parent: tkinter.Misc, view_model: WaitingViewModel, board: bool = False
    ):
        """On the board (fullscreen) there are no buttons, `Enter` confirms."""
        super().__init__(parent)
        self._view_model = view_model

        center = ttk.Frame(self)
        center.pack(expand=True)
        self._title = ttk.Label(
            center,
            text=view_model.next_title(),
            font=("TkDefaultFont", sizes_for(1.0).title_font),
        )
        self._title.pack(pady=(0, 24))

        if not board:
            self._build_buttons(center)
        ScaleWatcher(self, self._apply_scale)

    def _build_buttons(self, center: ttk.Frame) -> None:
        # The buttons do not take focus, so that Space on them is only the hotkey.
        buttons = ttk.Frame(center)
        buttons.pack()
        ttk.Button(
            buttons,
            text=t("waiting.next"),
            command=view_model.confirm,
            width=10,
            bootstyle="success",
            takefocus=False,
        ).pack(side="left", padx=4)
        ttk.Button(
            buttons,
            text=t("running.stop"),
            command=self._stop,
            width=10,
            bootstyle="danger",
            takefocus=False,
        ).pack(side="left", padx=4)

    def _apply_scale(self, scale: float) -> None:
        self._title.configure(font=("TkDefaultFont", sizes_for(scale).title_font))

    def _stop(self) -> None:
        answer = Messagebox.yesno(
            message=t("waiting.stop_confirm"),
            title=t("running.stop"),
            parent=self,
            localize=False,
        )
        if answer == "Yes":
            self._view_model.stop()

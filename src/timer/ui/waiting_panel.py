"""The home screen while the engine waits for confirmation: what comes next and the buttons."""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.waiting_view_model import WaitingViewModel
from ttkbootstrap.dialogs import Messagebox


class WaitingPanel(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: WaitingViewModel):
        super().__init__(parent)
        self._view_model = view_model

        center = ttk.Frame(self)
        center.pack(expand=True)
        ttk.Label(
            center, text=view_model.next_title(), font=("TkDefaultFont", 28)
        ).pack(pady=(0, 24))

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

    def _stop(self) -> None:
        answer = Messagebox.yesno(
            message=t("waiting.stop_confirm"),
            title=t("running.stop"),
            parent=self,
            localize=False,
        )
        if answer == "Yes":
            self._view_model.stop()

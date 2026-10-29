"""The home screen while a flow runs: the interval, the countdown and the buttons."""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.running_view_model import RunningViewModel
from ttkbootstrap.dialogs import Messagebox


SWATCH_SIZE = 28  # as high as the title


class RunningPanel(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: RunningViewModel):
        super().__init__(parent)
        self._view_model = view_model

        center = ttk.Frame(self)
        center.pack(expand=True)
        title_row = ttk.Frame(center)
        title_row.pack()
        # A circle in the color of the category stands before the title of a work interval.
        self._swatch = tkinter.Canvas(
            title_row,
            width=SWATCH_SIZE,
            height=SWATCH_SIZE,
            background=ttk.Style().lookup("TFrame", "background"),
            highlightthickness=0,
        )
        self._shown_color: str | None = None
        self._title = ttk.Label(title_row, font=("TkDefaultFont", 28))
        self._title.pack(side="left")
        self._number = ttk.Label(center, font=("TkDefaultFont", 12))
        self._number.pack(pady=(4, 0))
        self._countdown = ttk.Label(center, font=("TkDefaultFont", 72, "bold"))
        self._countdown.pack(pady=24)

        # The buttons do not take focus, so that Space on them is only the hotkey.
        buttons = ttk.Frame(center)
        buttons.pack()
        self._pause_button = ttk.Button(
            buttons, command=self._toggle_pause, width=10, takefocus=False
        )
        self._pause_button.pack(side="left", padx=4)
        ttk.Button(
            buttons,
            text=t("running.skip"),
            command=self._skip,
            width=10,
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

        self.refresh()

    def refresh(self) -> None:
        """Show the state of the engine now; called several times a second."""
        self._title.configure(text=self._view_model.title())
        self._show_color(self._view_model.color())
        self._number.configure(
            text=t(
                "running.work_interval_number",
                number=self._view_model.work_interval_number(),
            )
        )
        self._countdown.configure(text=self._view_model.countdown())
        self._pause_button.configure(text=self._view_model.pause_button_text())

    def _show_color(self, color: str | None) -> None:
        if color == self._shown_color:
            return
        self._shown_color = color
        if color is None:  # a break
            self._swatch.pack_forget()
            return
        self._swatch.delete("all")
        self._swatch.create_oval(
            2, 2, SWATCH_SIZE - 2, SWATCH_SIZE - 2, fill=color, outline=""
        )
        self._swatch.pack(side="left", padx=(0, 12), before=self._title)

    def _toggle_pause(self) -> None:
        self._view_model.toggle_pause()
        self.refresh()

    def _skip(self) -> None:
        self._view_model.skip()
        self.refresh()

    def _stop(self) -> None:
        answer = Messagebox.yesno(
            message=t("running.stop_confirm"),
            title=t("running.stop"),
            parent=self,
            localize=False,
        )
        if answer == "Yes":
            self._view_model.stop()

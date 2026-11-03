"""The home screen while a flow runs: the interval, the countdown and the buttons."""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.progress_row import ProgressRow
from timer.ui.running_view_model import RunningViewModel
from timer.ui.scale_watcher import ScaleWatcher
from timer.ui.scaling import sizes_for
from ttkbootstrap.dialogs import Messagebox


class RunningPanel(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: RunningViewModel):
        super().__init__(parent)
        self._view_model = view_model
        self._sizes = sizes_for(1.0)  # the fonts and circles grow with the window

        center = ttk.Frame(self)
        center.pack(expand=True, fill="x")
        title_row = ttk.Frame(center)
        title_row.pack()
        # A circle in the color of the category stands before the title of a work interval.
        self._swatch = tkinter.Canvas(
            title_row,
            width=self._sizes.swatch,
            height=self._sizes.swatch,
            background=ttk.Style().lookup("TFrame", "background"),
            highlightthickness=0,
        )
        self._shown_color: str | None = None
        self._title = ttk.Label(title_row, font=("TkDefaultFont", self._sizes.title_font))
        self._title.pack(side="left")
        self._number = ttk.Label(center, font=("TkDefaultFont", self._sizes.number_font))
        self._number.pack(pady=(4, 0))
        self._countdown = ttk.Label(
            center, font=("TkDefaultFont", self._sizes.countdown_font, "bold")
        )
        self._countdown.pack(pady=24)
        # The circle row is shown for a scenario only, between the countdown and the buttons.
        progress_place = ttk.Frame(center)
        progress_place.pack(fill="x", padx=24)
        self._progress_row = ProgressRow(progress_place, centered=True)
        self._progress_row.set_blink(view_model.blink())
        self._progress_row_is_shown = False

        # The buttons do not take focus, so that Space on them is only the hotkey.
        buttons = ttk.Frame(center)
        buttons.pack(pady=(24, 0))
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
        ScaleWatcher(self, self._apply_scale)

    def _apply_scale(self, scale: float) -> None:
        sizes = sizes_for(scale)
        self._sizes = sizes
        self._title.configure(font=("TkDefaultFont", sizes.title_font))
        self._number.configure(font=("TkDefaultFont", sizes.number_font))
        self._countdown.configure(font=("TkDefaultFont", sizes.countdown_font, "bold"))
        self._swatch.configure(width=sizes.swatch, height=sizes.swatch)
        self._progress_row.set_sizes(sizes)
        self._shown_color = None  # the swatch is drawn again, at its new size
        self.refresh()

    def refresh(self) -> None:
        """Show the state of the engine now; called several times a second."""
        self._title.configure(text=self._view_model.title())
        self._show_color(self._view_model.color())
        self._number.configure(text=self._view_model.number_text())
        self._countdown.configure(text=self._view_model.countdown())
        self._show_progress(self._view_model.progress_items())
        self._pause_button.configure(text=self._view_model.pause_button_text())

    def _show_progress(self, items) -> None:
        if items is None:
            if self._progress_row_is_shown:
                self._progress_row.pack_forget()
                self._progress_row_is_shown = False
            return
        if not self._progress_row_is_shown:
            self._progress_row.pack(fill="x")
            self._progress_row_is_shown = True
        self._progress_row.show(items)

    def _show_color(self, color: str | None) -> None:
        if color == self._shown_color:
            return
        self._shown_color = color
        if color is None:  # a break
            self._swatch.pack_forget()
            return
        self._swatch.delete("all")
        size = self._sizes.swatch
        self._swatch.create_oval(2, 2, size - 2, size - 2, fill=color, outline="")
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

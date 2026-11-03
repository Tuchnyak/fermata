"""A slider for a whole number that moves in steps: tick marks at every step, the values of
some of them written below, the chosen value shown at the right of the slider."""

import tkinter

import ttkbootstrap as ttk

TICKS_HEIGHT = 24
TICK_LENGTH = 4
LABELED_TICK_LENGTH = 7
LABEL_GAP = 2
RETRY_MILLISECONDS = 20


class NumberSlider(ttk.Frame):
    def __init__(
        self,
        parent: tkinter.Misc,
        lowest: int,
        highest: int,
        step: int,
        labeled_values: tuple[int, ...],
        length: int,
    ):
        super().__init__(parent)
        self._lowest = lowest
        self._highest = highest
        self._step = step
        self._labeled_values = labeled_values
        self._value = tkinter.DoubleVar(value=lowest)

        self._scale = ttk.Scale(
            self,
            from_=lowest,
            to=highest,
            length=length,
            variable=self._value,
            command=self._snap_to_step,
        )
        self._scale.grid(row=0, column=0)
        # The arrow keys move by a whole step; the library's own binding would move by 1.
        for key, direction in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
            self._scale.bind(f"<{key}>", lambda event, d=direction: self._move(d))

        style = ttk.Style()
        self._tick_color = style.lookup("TLabel", "foreground")
        self._ticks = tkinter.Canvas(
            self,
            width=length,
            height=TICKS_HEIGHT,
            background=style.lookup("TFrame", "background"),
            highlightthickness=0,
        )
        self._ticks.grid(row=1, column=0)
        # `coords` answers correctly only after the slider has been laid out and painted for the
        # first time; before that it puts the first tick at 0 and the last at the full width.
        # So the ticks are drawn once that is so, and again whenever the size changes.
        self._drawn_positions: list[float] = []
        self._draw_is_scheduled = False
        self._scale.bind("<Configure>", lambda event: self._draw_ticks())
        self._draw_ticks()

        self._readout = ttk.Label(self, width=4, anchor="e")
        self._readout.grid(row=0, column=1, rowspan=2, padx=(8, 0))

    def refresh_colors(self) -> None:
        """Take the colors of the theme in force now, after the theme was changed."""
        style = ttk.Style()
        self._tick_color = style.lookup("TLabel", "foreground")
        self._ticks.configure(background=style.lookup("TFrame", "background"))
        self._drawn_positions = []  # draw the ticks again
        self._draw_ticks()

    def get(self) -> str:
        return str(round(self._value.get()))

    def set(self, number: int) -> None:
        number = self._nearest_step(number)
        self._value.set(number)
        self._readout.configure(text=str(number))

    def _nearest_step(self, number: float) -> int:
        steps = round((number - self._lowest) / self._step)
        return min(max(self._lowest + steps * self._step, self._lowest), self._highest)

    def _snap_to_step(self, position: str) -> None:
        self.set(self._nearest_step(float(position)))

    def _move(self, direction: int) -> str:
        self.set(round(self._value.get()) + direction * self._step)
        return "break"

    def _retry_draw_ticks(self) -> None:
        self._draw_is_scheduled = False
        self._draw_ticks()

    def _draw_ticks(self) -> None:
        if self._scale.coords(self._lowest)[0] <= 0:  # the slider is not laid out yet
            if not self._draw_is_scheduled:
                self._draw_is_scheduled = True
                self.after(RETRY_MILLISECONDS, self._retry_draw_ticks)
            return
        tick_values = range(self._lowest, self._highest + 1, self._step)
        positions = [self._scale.coords(tick_value)[0] for tick_value in tick_values]
        if positions == self._drawn_positions:
            return
        self._drawn_positions = positions

        self._ticks.delete("all")
        for tick_value, x in zip(tick_values, positions):
            if tick_value in self._labeled_values:
                self._ticks.create_line(
                    x, 0, x, LABELED_TICK_LENGTH, fill=self._tick_color
                )
                self._ticks.create_text(
                    x,
                    LABELED_TICK_LENGTH + LABEL_GAP,
                    text=str(tick_value),
                    anchor="n",
                    fill=self._tick_color,
                    font=("TkDefaultFont", 8),
                )
            else:
                self._ticks.create_line(x, 0, x, TICK_LENGTH, fill=self._tick_color)

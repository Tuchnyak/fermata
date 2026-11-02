"""The widget that draws the circle row of a scenario (spec section 9)."""

import tkinter
from collections.abc import Sequence

import ttkbootstrap as ttk
from timer.ui.progress import (
    Circle,
    CircleState,
    ProgressItem,
    arrange,
    faded,
)

CIRCLE_SIZE = 20
SPACING = 8
OUTLINE_WIDTH = 2
FADE_AMOUNT = 0.6  # how far a skipped circle moves towards the background


class ProgressRow(tkinter.Canvas):
    def __init__(self, parent: tkinter.Misc):
        style = ttk.Style()
        self._background = style.lookup("TFrame", "background")
        self._accent = style.colors.primary
        super().__init__(
            parent,
            height=CIRCLE_SIZE + 2,
            background=self._background,
            highlightthickness=0,
        )
        self._items: Sequence[ProgressItem] = []
        self._drawn: tuple[int, Sequence[ProgressItem]] | None = None
        self.bind("<Configure>", lambda event: self._draw())

    def show(self, items: Sequence[ProgressItem]) -> None:
        self._items = items
        self._draw()

    def _draw(self) -> None:
        width = self.winfo_width()
        if self._drawn == (width, self._items):
            return
        self._drawn = (width, self._items)

        self.delete("all")
        placements = arrange(self._items, width, CIRCLE_SIZE, SPACING)
        for placement in placements:
            self._draw_circle(placement.x + 1, placement.y + 1, placement.circle)
        if placements:
            lines_height = max(placement.y for placement in placements) + CIRCLE_SIZE + 2
            self.configure(height=lines_height)

    def _draw_circle(self, x: int, y: int, circle: Circle) -> None:
        left, top = x + OUTLINE_WIDTH // 2, y + OUTLINE_WIDTH // 2
        right = x + CIRCLE_SIZE - OUTLINE_WIDTH // 2
        bottom = y + CIRCLE_SIZE - OUTLINE_WIDTH // 2
        if circle.state == CircleState.DONE:
            self.create_oval(left, top, right, bottom, fill=circle.color, outline="")
        elif circle.state == CircleState.SKIPPED:
            muted = faded(circle.color, self._background, FADE_AMOUNT)
            self.create_oval(left, top, right, bottom, fill=muted, outline="")
        elif circle.state == CircleState.CURRENT:
            self.create_oval(left, top, right, bottom, fill=self._accent, outline="")
        else:
            self.create_oval(
                left, top, right, bottom, outline=circle.color, width=OUTLINE_WIDTH
            )

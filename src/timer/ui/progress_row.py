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
BLINK_FADE_AMOUNT = 0.7  # the current circle dims this far, towards the background, and back
BLINK_MILLISECONDS = 600


class ProgressRow(tkinter.Canvas):
    def __init__(self, parent: tkinter.Misc, centered: bool = False):
        self._centered = centered
        style = ttk.Style()
        self._background = style.lookup("TFrame", "background")
        super().__init__(
            parent,
            height=CIRCLE_SIZE + 2,
            background=self._background,
            highlightthickness=0,
        )
        self._items: Sequence[ProgressItem] = []
        self._drawn: tuple[int, Sequence[ProgressItem], bool] | None = None
        self._blink = False
        self._current_is_dim = False
        self._blink_job: str | None = None
        self.bind("<Configure>", lambda event: self._draw())

    def show(self, items: Sequence[ProgressItem]) -> None:
        self._items = items
        self._draw()

    def set_blink(self, enabled: bool) -> None:
        """Make the current circle blink, or stop it."""
        self._blink = enabled
        self._current_is_dim = False
        if enabled and self._blink_job is None:
            self._blink_job = self.after(BLINK_MILLISECONDS, self._blink_step)
        self._draw()

    def destroy(self) -> None:
        if self._blink_job is not None:
            self.after_cancel(self._blink_job)
            self._blink_job = None
        super().destroy()

    def _blink_step(self) -> None:
        self._blink_job = None
        if not self._blink:
            return
        self._current_is_dim = not self._current_is_dim
        self._draw()
        self._blink_job = self.after(BLINK_MILLISECONDS, self._blink_step)

    def _draw(self) -> None:
        width = self.winfo_width()
        # Without blinking the current circle stays dimmed: at the full color it would look done.
        dim = self._current_is_dim or not self._blink
        if self._drawn == (width, self._items, dim):
            return
        self._drawn = (width, self._items, dim)

        self.delete("all")
        placements = arrange(self._items, width, CIRCLE_SIZE, SPACING)
        left_margin = 0
        if self._centered and placements:
            block_width = max(placement.x for placement in placements) + CIRCLE_SIZE + 2
            left_margin = max(0, (width - block_width) // 2)
        for placement in placements:
            self._draw_circle(
                left_margin + placement.x + 1, placement.y + 1, placement.circle, dim
            )
        if placements:
            lines_height = max(placement.y for placement in placements) + CIRCLE_SIZE + 2
            self.configure(height=lines_height)

    def _draw_circle(self, x: int, y: int, circle: Circle, dim: bool) -> None:
        left, top = x + OUTLINE_WIDTH // 2, y + OUTLINE_WIDTH // 2
        right = x + CIRCLE_SIZE - OUTLINE_WIDTH // 2
        bottom = y + CIRCLE_SIZE - OUTLINE_WIDTH // 2
        # The outline is drawn centered on the edge, so it reaches out by half its width: every
        # circle has one, or a filled circle would come out smaller than an outlined one.
        if circle.state == CircleState.DONE:
            self.create_oval(
                left,
                top,
                right,
                bottom,
                fill=circle.color,
                outline=circle.color,
                width=OUTLINE_WIDTH,
            )
        elif circle.state == CircleState.SKIPPED:
            muted = faded(circle.color, self._background, FADE_AMOUNT)
            self.create_oval(
                left, top, right, bottom, fill=muted, outline=muted, width=OUTLINE_WIDTH
            )
        elif circle.state == CircleState.CURRENT:
            # The edge is in the color of the category, like a done circle's; the fill is what
            # sets it apart: it is dimmed, and blinking brings it to the full color and back.
            fill = circle.color
            if dim:
                fill = faded(circle.color, self._background, BLINK_FADE_AMOUNT)
            self.create_oval(
                left,
                top,
                right,
                bottom,
                fill=fill,
                outline=circle.color,
                width=OUTLINE_WIDTH,
            )
        else:
            self.create_oval(
                left, top, right, bottom, outline=circle.color, width=OUTLINE_WIDTH
            )

"""The widget that draws the circle row of a scenario (spec section 9)."""

import tkinter
from collections.abc import Sequence

import ttkbootstrap as ttk
from PIL import ImageTk
from fermata.ui.circle_image import render_circle
from fermata.ui.progress import (
    Circle,
    CircleState,
    ProgressItem,
    arrange,
    faded,
)
from fermata.ui.scaling import Sizes, sizes_for

FADE_AMOUNT = 0.6  # how far a skipped circle moves towards the background
BLINK_FADE_AMOUNT = 0.7  # the current circle dims this far, towards the background, and back
BLINK_MILLISECONDS = 600


class ProgressRow(tkinter.Canvas):
    def __init__(self, parent: tkinter.Misc, centered: bool = False):
        self._centered = centered
        self._sizes = sizes_for(1.0)
        style = ttk.Style()
        self._background = style.lookup("TFrame", "background")
        super().__init__(
            parent,
            height=self._sizes.circle + 2,
            background=self._background,
            highlightthickness=0,
        )
        self._items: Sequence[ProgressItem] = []
        self._drawn: tuple[int, Sequence[ProgressItem], bool, Sizes] | None = None
        self._blink = False
        self._current_is_dim = False
        self._blink_job: str | None = None
        # The pictures on the canvas, by what they show; Tk draws only the ones it is holding.
        self._pictures: dict[tuple[int, int, str, str | None], ImageTk.PhotoImage] = {}
        self.bind("<Configure>", lambda event: self._draw())

    def show(self, items: Sequence[ProgressItem]) -> None:
        self._items = items
        self._draw()

    def set_sizes(self, sizes: Sizes) -> None:
        """Draw the circles at these sizes (they grow with the window)."""
        self._sizes = sizes
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
        if self._drawn == (width, self._items, dim, self._sizes):
            return
        self._drawn = (width, self._items, dim, self._sizes)

        self.delete("all")
        self._pictures.clear()
        circle_size = self._sizes.circle
        placements = arrange(self._items, width, circle_size, self._sizes.circle_spacing)
        left_margin = 0
        if self._centered and placements:
            block_width = max(placement.x for placement in placements) + circle_size + 2
            left_margin = max(0, (width - block_width) // 2)
        for placement in placements:
            self._draw_circle(
                left_margin + placement.x + 1, placement.y + 1, placement.circle, dim
            )
        if placements:
            lines_height = max(placement.y for placement in placements) + circle_size + 2
            self.configure(height=lines_height)

    def _draw_circle(self, x: int, y: int, circle: Circle, dim: bool) -> None:
        # Every circle has an outline, or a filled circle would come out smaller than an
        # outlined one.
        if circle.state == CircleState.DONE:
            outline, fill = circle.color, circle.color
        elif circle.state == CircleState.SKIPPED:
            outline = fill = faded(circle.color, self._background, FADE_AMOUNT)
        elif circle.state == CircleState.CURRENT:
            # The edge is in the color of the category, like a done circle's; the fill is what
            # sets it apart: it is dimmed, and blinking brings it to the full color and back.
            outline, fill = circle.color, circle.color
            if dim:
                fill = faded(circle.color, self._background, BLINK_FADE_AMOUNT)
        else:
            outline, fill = circle.color, None
        self.create_image(x, y, image=self._picture(outline, fill), anchor="nw")

    def _picture(self, outline: str, fill: str | None) -> ImageTk.PhotoImage:
        key = (self._sizes.circle, self._sizes.outline, outline, fill)
        if key not in self._pictures:
            image = render_circle(self._sizes.circle, self._sizes.outline, outline, fill)
            self._pictures[key] = ImageTk.PhotoImage(image)
        return self._pictures[key]

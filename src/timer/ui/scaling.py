"""How the screens grow with the window (spec section 11), without any Tk.

The size of a panel gives a scale: 1 at the size the panel has in the window of the first
launch. The sizes of the fonts and of the circles are their base sizes times the scale.
"""

from dataclasses import dataclass

REFERENCE_SIZE = (704, 615)  # the panel in the default window, 720 x 680, below its header
MIN_SCALE = 0.7
MAX_SCALE = 4.0
STEP = 0.05  # the scale changes in steps, so that dragging a corner does not redo the layout at every pixel


@dataclass(frozen=True)
class Sizes:
    title_font: int
    number_font: int
    countdown_font: int
    heading_font: int
    swatch: int  # the circle of the category before the title
    circle: int  # a circle of the progress row
    circle_spacing: int
    outline: int  # the edge of a circle


def scale_for(width: int, height: int) -> float:
    """The scale of a panel of this size: its smaller side relative to the reference size, in
    steps, between the lowest and the highest scale."""
    if width <= 1 or height <= 1:  # not laid out yet
        return MIN_SCALE
    raw = min(width / REFERENCE_SIZE[0], height / REFERENCE_SIZE[1])
    stepped = round(round(raw / STEP) * STEP, 2)
    return min(max(stepped, MIN_SCALE), MAX_SCALE)


def _scaled(base: int, scale: float) -> int:
    return max(1, round(base * scale))


def sizes_for(scale: float) -> Sizes:
    return Sizes(
        title_font=_scaled(28, scale),
        number_font=_scaled(12, scale),
        countdown_font=_scaled(72, scale),
        heading_font=_scaled(20, scale),
        swatch=_scaled(28, scale),
        circle=_scaled(20, scale),
        circle_spacing=_scaled(8, scale),
        outline=_scaled(2, scale),
    )

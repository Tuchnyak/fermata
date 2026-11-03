"""A circle of the progress row as a smooth picture (no Tk).

Tk's canvas draws ovals without smoothing, which shows at large sizes. A circle is drawn here
larger and scaled down by averaging (a box filter: Lanczos would overshoot at the edges and
change the colors), which smooths its edge; the picture has a transparent background, so
it fits any theme.
"""

from PIL import Image, ImageChops, ImageColor, ImageDraw

SUPERSAMPLE = 4  # the circle is drawn this many times larger, then scaled down


def render_circle(size: int, edge: int, outline: str, fill: str | None = None) -> Image.Image:
    """A `size` × `size` RGBA picture: a ring `edge` wide in `outline`, filled with `fill`.

    Without a fill the inside of the ring is transparent.
    """
    big = size * SUPERSAMPLE
    ring_width = edge * SUPERSAMPLE
    whole = _disc(big, 0)
    inside = _disc(big, ring_width)
    ring = ImageChops.subtract(whole, inside)

    colors = Image.new("RGB", (big, big), ImageColor.getrgb(outline))
    if fill is None:
        shape = ring
    else:
        colors.paste(Image.new("RGB", (big, big), ImageColor.getrgb(fill)), mask=inside)
        shape = whole
    picture = colors.convert("RGBA")
    picture.putalpha(shape)
    return picture.resize((size, size), Image.Resampling.BOX)


def _disc(size: int, inset: int) -> Image.Image:
    """A mask: white inside the circle that fills the square less `inset` on every side."""
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, size - 1 - inset, size - 1 - inset), fill=255)
    return mask

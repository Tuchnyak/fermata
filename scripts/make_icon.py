"""Draws the icon of the program, `src/fermata/icons/fermata.svg` and `fermata.png`, from one shape.

Run `uv run python scripts/make_icon.py` after changing the shape below; both files are
committed, and a test checks that they are what this script draws.

The icon ("Sunset"): a tile of warm white with rounded corners; a red sun, the dot of the
fermata, setting behind a black horizon that fills the bottom of the tile; above it the arc of
the fermata, thick in the middle and thin at the ends. The colors are the sign of the program
and do not follow its theme. Everything is in a square of 128 units.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ICONS = Path(__file__).parents[1] / "src" / "fermata" / "icons"

WARM_WHITE = "#f7f4ee"
RED = "#bc002d"
INK = "#1b1b1b"

SIZE = 128
TILE = (4, 4, 124, 124)  # left, top, right, bottom
TILE_RADIUS = 26
SUN_CENTER = (64, 92)
SUN_RADIUS = 24
HORIZON_TOP = 96
ARC_CENTER = (64, 70)  # the arc stands on y = 70
ARC_OUTER_RADIUS = 38
ARC_INNER_HALF_WIDTH = 33.5
ARC_INNER_HEIGHT = 25  # the middle of the arc is 38 - 25 = 13 thick, its ends 4.5

PNG_SIZE = 256
SCALE_UP = 8  # the picture is drawn this many times larger than the 128 units, then scaled down


def icon_svg() -> str:
    cx, base = ARC_CENTER
    left, right = cx - ARC_OUTER_RADIUS, cx + ARC_OUTER_RADIUS
    inner_left, inner_right = cx - ARC_INNER_HALF_WIDTH, cx + ARC_INNER_HALF_WIDTH
    arc = (
        f"M {left} {base} A {ARC_OUTER_RADIUS} {ARC_OUTER_RADIUS} 0 0 1 {right} {base} "
        f"L {inner_right:g} {base} A {ARC_INNER_HALF_WIDTH:g} {ARC_INNER_HEIGHT} 0 0 0 "
        f"{inner_left:g} {base} Z"
    )
    x0, y0, x1, y1 = TILE
    sun_x, sun_y = SUN_CENTER
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="{PNG_SIZE}" height="{PNG_SIZE}">
  <title>Fermata</title>
  <defs>
    <clipPath id="tile"><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{TILE_RADIUS}"/></clipPath>
  </defs>
  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{TILE_RADIUS}" fill="{WARM_WHITE}"/>
  <g clip-path="url(#tile)">
    <circle cx="{sun_x}" cy="{sun_y}" r="{SUN_RADIUS}" fill="{RED}"/>
    <rect x="{x0}" y="{HORIZON_TOP}" width="{x1 - x0}" height="{y1 - HORIZON_TOP}" fill="{INK}"/>
  </g>
  <path d="{arc}" fill="{INK}"/>
</svg>
"""


def _arc_polygon() -> list[tuple[float, float]]:
    """The outline of the arc, in the units of the picture drawn larger."""
    cx, base = ARC_CENTER
    steps = 360
    outer = []
    inner = []
    for step in range(steps + 1):
        angle = math.pi * step / steps
        outer.append((cx - ARC_OUTER_RADIUS * math.cos(angle), base - ARC_OUTER_RADIUS * math.sin(angle)))
        inner.append(
            (
                cx - ARC_INNER_HALF_WIDTH * math.cos(math.pi - angle),
                base - ARC_INNER_HEIGHT * math.sin(math.pi - angle),
            )
        )
    return [(x * SCALE_UP, y * SCALE_UP) for x, y in outer + inner]


def icon_png() -> Image.Image:
    """The picture drawn larger and scaled down by averaging, so that its edges are smooth."""
    side = SIZE * SCALE_UP
    x0, y0, x1, y1 = (value * SCALE_UP for value in TILE)
    tile = Image.new("L", (side, side), 0)
    ImageDraw.Draw(tile).rounded_rectangle((x0, y0, x1, y1), radius=TILE_RADIUS * SCALE_UP, fill=255)

    art = Image.new("RGBA", (side, side), WARM_WHITE)
    draw = ImageDraw.Draw(art)
    sun_x, sun_y = SUN_CENTER
    r = SUN_RADIUS
    draw.ellipse(((sun_x - r) * SCALE_UP, (sun_y - r) * SCALE_UP, (sun_x + r) * SCALE_UP, (sun_y + r) * SCALE_UP), fill=RED)
    draw.rectangle((0, HORIZON_TOP * SCALE_UP, side, side), fill=INK)
    draw.polygon(_arc_polygon(), fill=INK)

    picture = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    picture.paste(art, (0, 0), tile)
    return picture.resize((PNG_SIZE, PNG_SIZE), Image.Resampling.BOX)


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    (ICONS / "fermata.svg").write_text(icon_svg(), encoding="utf-8")
    icon_png().save(ICONS / "fermata.png")
    print(f"wrote {ICONS / 'fermata.svg'} and {ICONS / 'fermata.png'}")


if __name__ == "__main__":
    main()

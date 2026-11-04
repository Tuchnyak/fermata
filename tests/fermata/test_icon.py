import importlib.util
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).parents[2]
ICONS = ROOT / "src" / "fermata" / "icons"
SVG = ICONS / "fermata.svg"
PNG = ICONS / "fermata.png"

WARM_WHITE = (247, 244, 238)
RED = (188, 0, 45)
INK = (27, 27, 27)


@pytest.fixture(scope="module")
def make_icon():
    spec = importlib.util.spec_from_file_location("make_icon", ROOT / "scripts" / "make_icon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def png():
    return Image.open(PNG).convert("RGBA")


def pixel(png, x, y):
    """A pixel of the 256 px picture, given in the 128-unit square the icon is drawn in."""
    return png.getpixel((round(x * 2), round(y * 2)))[:3]


def test_the_icon_files_are_in_the_package():
    assert SVG.is_file()
    assert PNG.is_file()


def test_the_png_is_a_square_of_256_pixels(png):
    assert png.size == (256, 256)


def test_the_corners_of_the_tile_are_transparent(png):
    for corner in ((0, 0), (255, 0), (0, 255), (255, 255)):
        assert png.getpixel(corner)[3] == 0


def test_the_tile_is_opaque_inside(png):
    assert png.getpixel((128, 128))[3] == 255
    assert png.getpixel((10, 128))[3] == 255  # the left edge, away from the rounded corners


def test_the_tile_is_warm_white(png):
    assert pixel(png, 14, 50) == WARM_WHITE
    assert pixel(png, 114, 50) == WARM_WHITE


def test_the_sun_is_red_and_sits_in_the_middle(png):
    assert pixel(png, 64, 86) == RED
    assert pixel(png, 64, 80) == RED


def test_the_horizon_is_black_and_fills_the_bottom(png):
    assert pixel(png, 64, 110) == INK
    assert pixel(png, 30, 118) == INK


def test_the_sun_sets_behind_the_horizon(png):
    assert pixel(png, 64, 100) == INK  # where the sun would be, under the horizon


def test_the_arc_is_black_and_thick_in_the_middle(png):
    assert pixel(png, 64, 36) == INK
    assert pixel(png, 64, 44) == INK  # the middle is 13 units thick: from 32 to 45
    assert pixel(png, 64, 50) == WARM_WHITE  # and under it the tile shows again


def test_the_arc_is_thin_at_its_ends(png):
    assert pixel(png, 28, 69) == INK
    assert pixel(png, 33, 69) == WARM_WHITE  # the end is 4.5 units wide: from 26 to 30.5


def test_the_icon_files_are_what_the_script_draws(make_icon, png):
    assert make_icon.icon_svg() == SVG.read_text(encoding="utf-8")
    assert make_icon.icon_png().tobytes() == png.tobytes()


def test_the_svg_names_the_colors_of_the_icon():
    text = SVG.read_text(encoding="utf-8")

    for color in ("#f7f4ee", "#bc002d", "#1b1b1b"):
        assert color in text

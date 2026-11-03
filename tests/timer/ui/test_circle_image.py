import pytest
from PIL import ImageChops, ImageColor, ImageOps
from timer.ui.circle_image import render_circle

OUTLINE = "#ff8800"
FILL = "#2255cc"


def rgba(color, alpha=255):
    return (*ImageColor.getrgb(color), alpha)


# --- the picture -------------------------------------------------------------


@pytest.mark.parametrize("size", [20, 33, 80])
def test_the_picture_has_the_size_asked_for(size):
    image = render_circle(size, 2, OUTLINE, FILL)

    assert image.size == (size, size)
    assert image.mode == "RGBA"


def test_the_corners_are_transparent():
    image = render_circle(20, 2, OUTLINE, FILL)

    for corner in [(0, 0), (19, 0), (0, 19), (19, 19)]:
        assert image.getpixel(corner)[3] == 0


def test_a_filled_circle_has_the_fill_in_the_middle():
    image = render_circle(20, 2, OUTLINE, FILL)

    assert image.getpixel((10, 10)) == rgba(FILL)


def test_the_ring_is_in_the_outline_color():
    image = render_circle(20, 2, OUTLINE, FILL)

    assert image.getpixel((1, 10)) == rgba(OUTLINE)
    assert image.getpixel((10, 1)) == rgba(OUTLINE)


def test_without_a_fill_the_inside_is_transparent():
    image = render_circle(20, 2, OUTLINE)

    assert image.getpixel((10, 10))[3] == 0
    assert image.getpixel((1, 10)) == rgba(OUTLINE)


def test_the_circle_reaches_all_four_sides_of_the_picture():
    image = render_circle(20, 2, OUTLINE, FILL)

    for side in [(0, 10), (19, 10), (10, 0), (10, 19)]:
        assert image.getpixel(side)[3] > 128


def test_the_ring_grows_with_its_width():
    thin = render_circle(40, 2, OUTLINE, FILL)
    thick = render_circle(40, 8, OUTLINE, FILL)

    assert thin.getpixel((5, 20)) == rgba(FILL)
    assert thick.getpixel((5, 20)) == rgba(OUTLINE)


# --- smoothing ---------------------------------------------------------------


def partly_transparent_pixels(image):
    alphas = image.getchannel("A").get_flattened_data()
    return [alpha for alpha in alphas if 0 < alpha < 255]


@pytest.mark.parametrize("fill", [FILL, None])
def test_the_edge_has_in_between_pixels(fill):
    image = render_circle(80, 8, OUTLINE, fill)

    assert len(partly_transparent_pixels(image)) > 40


def test_the_inner_edge_of_the_ring_is_smooth_too():
    image = render_circle(80, 8, OUTLINE, FILL)

    # a pixel on the diagonal of the inner edge is neither the outline nor the fill
    colors = {image.getpixel((x, x)) for x in range(8, 20)}
    assert any(color[:3] not in (rgba(OUTLINE)[:3], rgba(FILL)[:3]) for color in colors if color[3])


def test_no_dark_fringe_at_the_edge():
    image = render_circle(80, 8, "#ffffff")

    # the partly transparent pixels of a white ring are white, not grey
    for red, green, blue, alpha in image.get_flattened_data():
        if 0 < alpha < 255:
            assert min(red, green, blue) >= 250


@pytest.mark.parametrize("fill", [FILL, None])
def test_the_circle_is_symmetric(fill):
    image = render_circle(20, 2, OUTLINE, fill)

    assert ImageChops.difference(image, ImageOps.mirror(image)).getbbox() is None
    assert ImageChops.difference(image, ImageOps.flip(image)).getbbox() is None

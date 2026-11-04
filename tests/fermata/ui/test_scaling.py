import pytest
from fermata.ui.scaling import (
    MAX_SCALE,
    MIN_SCALE,
    REFERENCE_SIZE,
    STEP,
    Sizes,
    scale_for,
    sizes_for,
)

REFERENCE_WIDTH, REFERENCE_HEIGHT = REFERENCE_SIZE


# --- the scale -------------------------------------------------------------------


def test_the_reference_size_has_the_scale_one():
    assert scale_for(REFERENCE_WIDTH, REFERENCE_HEIGHT) == 1.0


def test_twice_the_reference_size_has_twice_the_scale():
    assert scale_for(2 * REFERENCE_WIDTH, 2 * REFERENCE_HEIGHT) == 2.0


def test_the_smaller_side_decides():
    assert scale_for(3 * REFERENCE_WIDTH, REFERENCE_HEIGHT) == 1.0
    assert scale_for(REFERENCE_WIDTH, 3 * REFERENCE_HEIGHT) == 1.0


def test_a_panel_too_small_has_the_lowest_scale():
    assert scale_for(100, 100) == MIN_SCALE


@pytest.mark.parametrize("size", [(0, 0), (1, 1), (-5, 600), (600, 0)])
def test_a_panel_that_is_not_laid_out_yet_has_the_lowest_scale(size):
    assert scale_for(*size) == MIN_SCALE


def test_a_panel_too_big_has_the_highest_scale():
    assert scale_for(100 * REFERENCE_WIDTH, 100 * REFERENCE_HEIGHT) == MAX_SCALE


def test_a_few_pixels_do_not_change_the_scale():
    assert scale_for(REFERENCE_WIDTH + 6, REFERENCE_HEIGHT + 5) == 1.0
    assert scale_for(REFERENCE_WIDTH - 6, REFERENCE_HEIGHT - 5) == 1.0


@pytest.mark.parametrize("pixels", range(300, 3000, 37))
def test_the_scale_goes_in_steps(pixels):
    scale = scale_for(pixels, pixels)

    assert round(scale / STEP) * STEP == pytest.approx(scale)


def test_a_bigger_window_never_has_a_smaller_scale():
    scales = [scale_for(width, width * 9 // 10) for width in range(200, 3000, 13)]

    assert scales == sorted(scales)


# --- the sizes -------------------------------------------------------------------


def test_the_sizes_at_scale_one_are_the_base_sizes():
    assert sizes_for(1.0) == Sizes(
        title_font=28,
        number_font=12,
        countdown_font=72,
        heading_font=20,
        swatch=28,
        circle=20,
        circle_spacing=8,
        outline=2,
    )


def test_the_sizes_double_with_the_scale():
    assert sizes_for(2.0) == Sizes(
        title_font=56,
        number_font=24,
        countdown_font=144,
        heading_font=40,
        swatch=56,
        circle=40,
        circle_spacing=16,
        outline=4,
    )


@pytest.mark.parametrize("scale", [MIN_SCALE, 0.85, 1.0, 1.35, 2.5, MAX_SCALE])
def test_every_size_is_a_whole_number_of_at_least_one(scale):
    for value in vars(sizes_for(scale)).values():
        assert isinstance(value, int) and value >= 1


def test_the_countdown_is_always_the_biggest_text():
    for scale in (MIN_SCALE, 1.0, MAX_SCALE):
        sizes = sizes_for(scale)
        assert sizes.countdown_font > sizes.title_font > sizes.number_font

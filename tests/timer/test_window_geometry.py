import pytest
from timer.window_geometry import (
    DEFAULT_SIZE,
    MIN_SIZE,
    WindowGeometry,
    fit_to_screen,
    parse_geometry,
    placement_offset,
    startup_geometry,
    without_offset,
)

SCREEN = (1920, 1080)


# --- the stored text ---------------------------------------------------------


def test_a_geometry_is_written_as_size_and_position():
    assert WindowGeometry(720, 680, 100, 50).as_text() == "720x680+100+50"


def test_a_negative_position_is_written_with_a_plus_and_a_minus():
    # "-5" alone would mean five pixels from the right edge of the screen
    assert WindowGeometry(720, 680, -5, -20).as_text() == "720x680+-5+-20"


@pytest.mark.parametrize(
    "geometry",
    [
        WindowGeometry(720, 680, 100, 50),
        WindowGeometry(520, 440, 0, 0),
        WindowGeometry(900, 700, -5, -20),
    ],
)
def test_the_written_text_is_read_back(geometry):
    assert parse_geometry(geometry.as_text()) == geometry


@pytest.mark.parametrize(
    "text",
    [
        "",
        "nonsense",
        "720x680",
        "720x680+100",
        "720x680-5+20",  # a position from the right edge is not our form
        "0x680+0+0",
        "720x0+0+0",
        "-720x680+0+0",
        "720.5x680+0+0",
        " 720x680+0+0",
        "720x680+0+0 ",
        "720X680+0+0",
        5,
        None,
    ],
)
def test_text_that_is_not_a_stored_geometry_is_not_read(text):
    assert parse_geometry(text) is None


# --- fitting to the screen ---------------------------------------------------


def test_a_window_on_the_screen_is_left_as_it_is():
    geometry = WindowGeometry(720, 680, 100, 50)

    assert fit_to_screen(geometry, *SCREEN) == geometry


def test_a_window_past_the_right_edge_is_moved_left_to_fit():
    geometry = WindowGeometry(720, 680, 1800, 50)

    assert fit_to_screen(geometry, *SCREEN) == WindowGeometry(720, 680, 1200, 50)


def test_a_window_past_the_bottom_edge_is_moved_up_to_fit():
    geometry = WindowGeometry(720, 680, 100, 900)

    assert fit_to_screen(geometry, *SCREEN) == WindowGeometry(720, 680, 100, 400)


def test_a_window_with_a_negative_position_is_moved_onto_the_screen():
    geometry = WindowGeometry(720, 680, -300, -40)

    assert fit_to_screen(geometry, *SCREEN) == WindowGeometry(720, 680, 0, 0)


def test_a_window_larger_than_the_screen_is_cut_down_to_it():
    geometry = WindowGeometry(3000, 2000, 500, 500)

    assert fit_to_screen(geometry, *SCREEN) == WindowGeometry(1920, 1080, 0, 0)


def test_a_window_smaller_than_the_minimum_is_made_the_minimum():
    geometry = WindowGeometry(100, 100, 10, 10)

    assert fit_to_screen(geometry, *SCREEN) == WindowGeometry(*MIN_SIZE, 10, 10)


def test_a_screen_smaller_than_the_minimum_wins_over_it():
    geometry = WindowGeometry(720, 680, 0, 0)

    assert fit_to_screen(geometry, 480, 400) == WindowGeometry(480, 400, 0, 0)


# --- at start ----------------------------------------------------------------


def test_with_nothing_stored_the_window_has_the_default_size_in_the_middle_of_the_screen():
    width, height = DEFAULT_SIZE
    x, y = (1920 - width) // 2, (1080 - height) // 2

    assert startup_geometry("", *SCREEN) == f"{width}x{height}+{x}+{y}"


def test_a_stored_geometry_that_cannot_be_read_gives_the_default_window():
    assert startup_geometry("garbage", *SCREEN) == startup_geometry("", *SCREEN)


def test_a_stored_geometry_on_the_screen_is_used_as_it_is():
    assert startup_geometry("900x700+100+50", *SCREEN) == "900x700+100+50"


def test_a_stored_geometry_off_the_screen_is_corrected():
    # saved on a larger monitor that is not connected now
    assert startup_geometry("900x700+3000+2000", *SCREEN) == "900x700+1020+380"


# --- where the window manager puts the window ----------------------------------


def test_a_window_put_where_it_was_asked_has_no_offset():
    assert placement_offset("800x600+150+120", "800x600+150+120") == (0, 0)


def test_the_offset_is_how_far_the_window_landed_from_the_position_asked_for():
    # the title bar of the window manager sits above the window Tk reports on
    assert placement_offset("800x600+150+120", "800x600+150+148") == (0, 28)
    assert placement_offset("800x600+150+120", "800x600+140+100") == (-10, -20)


def test_there_is_no_offset_when_either_text_cannot_be_read():
    assert placement_offset("garbage", "800x600+150+148") == (0, 0)
    assert placement_offset("800x600+150+120", "garbage") == (0, 0)


def test_the_offset_is_taken_off_the_position_to_ask_for():
    assert without_offset("800x600+150+148", (0, 28)) == "800x600+150+120"
    assert without_offset("800x600+150+148", (0, 0)) == "800x600+150+148"


def test_the_geometry_asked_for_lands_where_it_was_read_from():
    asked = "800x600+150+120"
    got = "800x600+150+148"  # the window manager adds 28 to the top

    offset = placement_offset(asked, got)

    assert without_offset(got, offset) == asked


def test_a_geometry_that_cannot_be_read_is_given_back_as_it_is():
    assert without_offset("garbage", (0, 28)) == "garbage"

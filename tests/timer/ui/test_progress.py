import pytest
from timer.ui.progress import (
    Circle,
    CircleState,
    LongBreakGap,
    Placement,
    arrange,
    faded,
    progress_items,
)

FUTURE = CircleState.FUTURE
SIZE = 10
SPACING = 4
SLOT = SIZE + SPACING


def circles(count):
    return [Circle(FUTURE, "#112233")] * count


def future(count):
    return [FUTURE] * count


def shape(items):
    """The items as letters: C for a circle, G for the gap of a long break."""
    return "".join("C" if isinstance(item, Circle) else "G" for item in items)


# --- the items -----------------------------------------------------------------


def test_a_circle_carries_its_state_and_the_color_of_its_category():
    items = progress_items(
        ["#111111", "#222222", "#333333"],
        [CircleState.DONE, CircleState.CURRENT, CircleState.FUTURE],
        long_break_every=4,
    )

    assert items == [
        Circle(CircleState.DONE, "#111111"),
        Circle(CircleState.CURRENT, "#222222"),
        Circle(CircleState.FUTURE, "#333333"),
    ]


def test_a_gap_stands_after_every_nth_circle():
    items = progress_items(["#112233"] * 6, future(6), long_break_every=4)

    assert shape(items) == "CCCCGCC"


def test_there_is_no_gap_after_the_last_circle():
    items = progress_items(["#112233"] * 4, future(4), long_break_every=4)

    assert shape(items) == "CCCC"


def test_the_gaps_repeat_with_every_nth_circle():
    items = progress_items(["#112233"] * 6, future(6), long_break_every=2)

    assert shape(items) == "CCGCCGCC"


def test_a_single_circle_has_no_gap():
    assert shape(progress_items(["#112233"], future(1), long_break_every=1)) == "C"


def test_no_circles_give_no_items():
    assert progress_items([], [], long_break_every=4) == []


# --- the placement -------------------------------------------------------------


def xs_and_ys(placements):
    return [(placement.x, placement.y) for placement in placements]


def test_circles_stand_in_a_row_one_slot_apart():
    placements = arrange(circles(3), line_width=1000, circle_size=SIZE, spacing=SPACING)

    assert xs_and_ys(placements) == [(0, 0), (SLOT, 0), (2 * SLOT, 0)]
    assert placements[0] == Placement(0, 0, circles(1)[0])


def test_a_gap_takes_one_slot():
    items = [*circles(2), LongBreakGap(), *circles(1)]

    placements = arrange(items, line_width=1000, circle_size=SIZE, spacing=SPACING)

    assert xs_and_ys(placements) == [(0, 0), (SLOT, 0), (3 * SLOT, 0)]


def test_circles_wrap_to_the_next_line_when_the_line_is_full():
    line_width = 3 * SLOT - SPACING  # three circles fit

    placements = arrange(circles(5), line_width, SIZE, SPACING)

    assert xs_and_ys(placements) == [
        (0, 0),
        (SLOT, 0),
        (2 * SLOT, 0),
        (0, SLOT),
        (SLOT, SLOT),
    ]


def test_a_gap_at_the_end_of_a_line_is_not_drawn_and_the_next_circle_starts_a_line():
    line_width = 2 * SLOT - SPACING  # two circles fit
    items = [*circles(2), LongBreakGap(), *circles(1)]

    placements = arrange(items, line_width, SIZE, SPACING)

    assert xs_and_ys(placements) == [(0, 0), (SLOT, 0), (0, SLOT)]


def test_a_gap_that_fills_the_line_ends_it():
    line_width = 3 * SLOT - SPACING  # three circles fit
    items = [*circles(2), LongBreakGap(), *circles(1)]

    placements = arrange(items, line_width, SIZE, SPACING)

    assert xs_and_ys(placements) == [(0, 0), (SLOT, 0), (0, SLOT)]


def test_a_line_does_not_start_with_a_gap():
    items = [LongBreakGap(), *circles(2)]

    placements = arrange(items, line_width=1000, circle_size=SIZE, spacing=SPACING)

    assert xs_and_ys(placements) == [(0, 0), (SLOT, 0)]


def test_a_very_narrow_line_still_holds_a_circle_per_line():
    placements = arrange(circles(2), line_width=1, circle_size=SIZE, spacing=SPACING)

    assert xs_and_ys(placements) == [(0, 0), (0, SLOT)]


# --- fading --------------------------------------------------------------------


def test_zero_amount_keeps_the_color():
    assert faded("#ff8040", "#000000", 0) == "#ff8040"


def test_full_amount_gives_the_background():
    assert faded("#ff8040", "#102030", 1) == "#102030"


def test_half_amount_is_halfway_to_the_background():
    assert faded("#ff0000", "#000000", 0.5) == "#800000"

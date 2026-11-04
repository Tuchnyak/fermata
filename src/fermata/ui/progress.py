"""The circle row of a scenario (spec section 9) without any Tk: which circles there are, how they
look and where they are placed."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto


class CircleState(Enum):
    DONE = auto()
    SKIPPED = auto()
    CURRENT = auto()
    FUTURE = auto()


@dataclass(frozen=True)
class Circle:
    state: CircleState
    color: str


@dataclass(frozen=True)
class LongBreakGap:
    """The space a long break takes in the row: one circle wide."""


type ProgressItem = Circle | LongBreakGap


@dataclass(frozen=True)
class Placement:
    x: int
    y: int
    circle: Circle


def progress_items(
    colors: Sequence[str], states: Sequence[CircleState], long_break_every: int
) -> list[ProgressItem]:
    """One circle per work interval, with a gap where a long break falls.

    A long break follows every `long_break_every`-th work interval except the last one: after
    the last work interval of a scenario there is no break.
    """
    items: list[ProgressItem] = []
    for index, (color, state) in enumerate(zip(colors, states)):
        items.append(Circle(state, color))
        is_last = index == len(colors) - 1
        if (index + 1) % long_break_every == 0 and not is_last:
            items.append(LongBreakGap())
    return items


def arrange(
    items: Sequence[ProgressItem], line_width: int, circle_size: int, spacing: int
) -> list[Placement]:
    """Place the circles on lines of the given width.

    A circle and a gap each take a slot (a circle's size and the spacing). A circle that does
    not fit goes to the next line; a gap at the start or at the end of a line is not drawn.
    """
    slot = circle_size + spacing
    slots_per_line = max(1, (line_width + spacing) // slot)
    placements = []
    line = 0
    column = 0
    for item in items:
        if isinstance(item, LongBreakGap):
            if 0 < column < slots_per_line:
                column += 1
            continue
        if column >= slots_per_line:
            line += 1
            column = 0
        placements.append(Placement(column * slot, line * slot, item))
        column += 1
    return placements


def _channels(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def faded(color: str, background: str, amount: float) -> str:
    """The color moved towards the background: 0 keeps it, 1 gives the background."""
    mixed = []
    for own, other in zip(_channels(color), _channels(background)):
        mixed.append(round(own * (1 - amount) + other * amount))
    return "#{:02x}{:02x}{:02x}".format(*mixed)

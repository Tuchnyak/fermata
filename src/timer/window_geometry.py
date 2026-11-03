"""The size and position of the main window as stored text, and how to fit them to the screen.

The text is `WIDTHxHEIGHT+X+Y` (a negative position as `+-N`), the form Tk accepts for
`geometry()`. No Tk is used here.
"""

import re
from dataclasses import dataclass

DEFAULT_SIZE = (720, 680)
MIN_SIZE = (520, 440)  # below this the screens would not fit

_GEOMETRY_PATTERN = re.compile(r"([0-9]+)x([0-9]+)\+(-?[0-9]+)\+(-?[0-9]+)")


@dataclass(frozen=True)
class WindowGeometry:
    width: int
    height: int
    x: int
    y: int

    def as_text(self) -> str:
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


def parse_geometry(text: object) -> WindowGeometry | None:
    """The geometry the text holds, or None if it is not in the stored form."""
    if not isinstance(text, str):
        return None
    match = _GEOMETRY_PATTERN.fullmatch(text)
    if match is None:
        return None
    width, height, x, y = (int(group) for group in match.groups())
    if width == 0 or height == 0:
        return None
    return WindowGeometry(width, height, x, y)


def fit_to_screen(
    geometry: WindowGeometry, screen_width: int, screen_height: int
) -> WindowGeometry:
    """The same window made at least the minimum size, no larger than the screen and on it."""
    min_width, min_height = MIN_SIZE
    width = min(max(geometry.width, min_width), screen_width)
    height = min(max(geometry.height, min_height), screen_height)
    x = min(max(geometry.x, 0), screen_width - width)
    y = min(max(geometry.y, 0), screen_height - height)
    return WindowGeometry(width, height, x, y)


def startup_geometry(stored_text: str, screen_width: int, screen_height: int) -> str:
    """What to give Tk at start: the stored window fitted to the screen, else the default one."""
    stored = parse_geometry(stored_text)
    if stored is None:
        width, height = DEFAULT_SIZE
        x, y = (screen_width - width) // 2, (screen_height - height) // 2
        stored = WindowGeometry(width, height, x, y)
    return fit_to_screen(stored, screen_width, screen_height).as_text()


def placement_offset(asked_text: str, got_text: str) -> tuple[int, int]:
    """How far the window manager put the window from the position asked for, as (dx, dy).

    The manager puts the window's frame at the position asked for, while Tk reports the position
    of the window below the title bar: reading a position and asking for it again would move the
    window down at every start.
    """
    asked = parse_geometry(asked_text)
    got = parse_geometry(got_text)
    if asked is None or got is None:
        return (0, 0)
    return (got.x - asked.x, got.y - asked.y)


def without_offset(got_text: str, offset: tuple[int, int]) -> str:
    """The geometry to ask for so that the window lands where `got_text` says it is now."""
    got = parse_geometry(got_text)
    if got is None:
        return got_text
    dx, dy = offset
    return WindowGeometry(got.width, got.height, got.x - dx, got.y - dy).as_text()

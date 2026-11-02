"""Validation rules for settings: which keys exist and which values each one accepts.

`RULES` maps a setting key to a `Rule`: a check for the value and the localization key of the
error to raise when the check fails. Adding a setting means adding its field to `Settings` and
its rule here.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial


# The limits and the modes are also what the settings screen offers.
WORK_MINUTES_RANGE = (1, 120)
SHORT_BREAK_MINUTES_RANGE = (1, 30)
LONG_BREAK_MINUTES_RANGE = (1, 60)
LONG_BREAK_EVERY_RANGE = (1, 10)
TRANSITION_MODES = ("auto", "confirm", "mixed")


@dataclass(frozen=True)
class Rule:
    is_valid: Callable[[object], bool]
    error_key: str


def _is_integer_within(value: object, limits: tuple[int, int]) -> bool:
    lowest, highest = limits
    # `type(...) is int` keeps `True` out: bool is a subclass of int.
    return type(value) is int and lowest <= value <= highest


def _integer_rule(limits: tuple[int, int], error_key: str) -> Rule:
    return Rule(partial(_is_integer_within, limits=limits), error_key)


def _is_transition_mode(value: object) -> bool:
    return value in TRANSITION_MODES


def _is_flag(value: object) -> bool:
    return type(value) is bool


RULES = {
    "work_minutes": _integer_rule(WORK_MINUTES_RANGE, "setting.work_minutes_invalid"),
    "short_break_minutes": _integer_rule(
        SHORT_BREAK_MINUTES_RANGE, "setting.short_break_minutes_invalid"
    ),
    "long_break_minutes": _integer_rule(
        LONG_BREAK_MINUTES_RANGE, "setting.long_break_minutes_invalid"
    ),
    "long_break_every": _integer_rule(
        LONG_BREAK_EVERY_RANGE, "setting.long_break_every_invalid"
    ),
    "transition_mode": Rule(_is_transition_mode, "setting.transition_mode_invalid"),
    "blink": Rule(_is_flag, "setting.blink_invalid"),
    "sound": Rule(_is_flag, "setting.sound_invalid"),
}

"""Validation rules for settings: which keys exist and which values each one accepts.

`RULES` maps a setting key to a `Rule`: a check for the value and the localization key of the
error to raise when the check fails. Adding a setting means adding its field to `Settings` and
its rule here.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    is_valid: Callable[[object], bool]
    error_key: str


def _is_integer_between(value: object, lowest: int, highest: int) -> bool:
    # `type(...) is int` keeps `True` out: bool is a subclass of int.
    return type(value) is int and lowest <= value <= highest


def _is_minutes(value: object) -> bool:
    return _is_integer_between(value, 1, 180)


def _is_long_break_every(value: object) -> bool:
    return _is_integer_between(value, 1, 20)


def _is_transition_mode(value: object) -> bool:
    return value in ("auto", "confirm", "mixed")


def _is_blink(value: object) -> bool:
    return type(value) is bool


RULES = {
    "work_minutes": Rule(_is_minutes, "setting.minutes_invalid"),
    "short_break_minutes": Rule(_is_minutes, "setting.minutes_invalid"),
    "long_break_minutes": Rule(_is_minutes, "setting.minutes_invalid"),
    "long_break_every": Rule(_is_long_break_every, "setting.long_break_every_invalid"),
    "transition_mode": Rule(_is_transition_mode, "setting.transition_mode_invalid"),
    "blink": Rule(_is_blink, "setting.blink_invalid"),
}

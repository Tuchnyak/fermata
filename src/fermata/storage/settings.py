"""Global settings: the typed `Settings` snapshot and the repository that reads and writes it.

Settings live in the `setting` table as key/value text (see docs/schema.md). Only changed
values are stored; a missing key means the default declared in `Settings`. Values are
validated by `settings_rules` before they are written.
"""

from dataclasses import dataclass, fields

from fermata.storage.db import Db
from fermata.storage.settings_rules import RULES
from fermata.validation import ValidationError

type Value = bool | int | str


@dataclass(frozen=True)
class Settings:
    """Global settings; a new setting is a new field with its default value."""

    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_every: int = 4
    transition_mode: str = "confirm"
    blink: bool = True
    sound: bool = True
    background_sound: str = "off"
    theme: str = "dark"
    language: str = "en"
    window_geometry: str = ""  # "" until the window has been closed once


def _encode(value: Value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _decode(kind: type, text: str) -> Value:
    if kind is bool:
        return text == "1"
    return kind(text)


class SettingsRepository:
    def __init__(self, db: Db):
        self._db = db

    def get_all(self) -> Settings:
        setting_text_by_key = dict(
            self._db.query(
                "SELECT key, value FROM setting",
                mapper=lambda row: (row["key"], row["value"]),
            )
        )
        setting_values = {}
        for field in fields(Settings):
            text = setting_text_by_key.get(field.name)
            if text is not None:
                setting_values[field.name] = _decode(field.type, text)
        return Settings(**setting_values)

    def set_many(self, changes: dict[str, Value]) -> None:
        """Store all the values or, if one is rejected, none of them."""
        with self._db.transaction():
            for key, value in changes.items():
                self.set(key, value)

    def set(self, key: str, value: Value) -> None:
        rule = RULES.get(key)
        if rule is None:
            raise ValidationError("setting.unknown_key")
        if not rule.is_valid(value):
            raise ValidationError(rule.error_key)
        self._db.execute(
            "INSERT INTO setting (key, value) VALUES (:key, :value)"
            " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            {"key": key, "value": _encode(value)},
        )

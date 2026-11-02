"""What the settings screen shows and does, without any Tk.

`save` answers with the message to show, already localized, or None when the values were saved.
"""

from timer.i18n import t
from timer.storage.settings import Settings, SettingsRepository, Value
from timer.validation import ValidationError


def _to_number(text: str) -> int | str:
    """A whole number as an int; anything else is left as text for the rules to reject."""
    try:
        return int(text)
    except ValueError:
        return text


class SettingsViewModel:
    def __init__(self, settings_repository: SettingsRepository):
        self._settings_repository = settings_repository

    def settings(self) -> Settings:
        return self._settings_repository.get_all()

    def save(
        self,
        *,
        work_minutes: str,
        short_break_minutes: str,
        long_break_minutes: str,
        long_break_every: str,
        transition_mode: str,
        blink: bool,
        sound: bool,
    ) -> str | None:
        entered: dict[str, Value] = {
            "work_minutes": _to_number(work_minutes),
            "short_break_minutes": _to_number(short_break_minutes),
            "long_break_minutes": _to_number(long_break_minutes),
            "long_break_every": _to_number(long_break_every),
            "transition_mode": transition_mode,
            "blink": blink,
            "sound": sound,
        }
        # Only what differs from the current settings is stored (see docs/schema.md).
        current = self.settings()
        changes = {}
        for key, value in entered.items():
            if value != getattr(current, key):
                changes[key] = value

        try:
            self._settings_repository.set_many(changes)
        except ValidationError as error:
            return t(error.key)
        return None

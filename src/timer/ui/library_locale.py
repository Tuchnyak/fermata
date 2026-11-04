"""The language of the texts that ttkbootstrap puts into its own dialogs.

The dialogs the application uses (a line of text to enter, the color chooser) translate their
buttons and labels through the library's message catalog, which knows some of the languages of
the application but not all; the missing translations are written here.
"""

from ttkbootstrap.localization import MessageCatalog

# The texts of the library dialogs that the application uses.
LIBRARY_STRINGS_USED = (
    "Submit",
    "Cancel",
    "OK",
    "Advanced",
    "Themed",
    "Standard",
    "Current",
    "New",
    "Hue",
    "Sat",
    "Lum",
    "Hex",
    "Red",
    "Green",
    "Blue",
)

RUSSIAN = {
    "Submit": "Применить",
    "Cancel": "Отмена",
    "OK": "ОК",
    "Advanced": "Дополнительно",
    "Themed": "Темы",
    "Standard": "Стандартные",
    "Current": "Текущий",
    "New": "Новый",
    "Hue": "Тон",
    "Sat": "Нас",
    "Lum": "Ярк",
    "Hex": "Hex",
    "Red": "Красный",
    "Green": "Зелёный",
    "Blue": "Синий",
}

# The locale of the library for each language of the application, and the translations it lacks.
LIBRARY_LOCALES = {"en": "en", "ru": "ru"}
MISSING_TRANSLATIONS = {"ru": RUSSIAN}


def apply_library_locale(language: str) -> None:
    """Make the dialogs of the library speak the language; needs a window to exist."""
    locale = LIBRARY_LOCALES[language]
    for source, translated in MISSING_TRANSLATIONS.get(language, {}).items():
        MessageCatalog.set(locale, source, translated)
    MessageCatalog.locale(locale)

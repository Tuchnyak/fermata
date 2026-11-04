"""The language of the texts that ttkbootstrap puts into its own dialogs.

The dialogs the application uses (a line of text to enter, the color chooser) translate their
buttons and labels through the library's message catalog, which knows some of the languages of
the application but not all; the missing translations are written here.
"""

from ttkbootstrap.localization import MessageCatalog, msgs
from ttkbootstrap.localization.msgcat import normalize_locale

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

CHINESE = {
    "Advanced": "高级",
    "Themed": "主题",
    "Standard": "标准",
    "Current": "当前",
    "New": "新",
    "Hue": "色相",
    "Sat": "饱和度",
    "Lum": "亮度",
    "Hex": "十六进制",
    "Red": "红",
    "Green": "绿",
    "Blue": "蓝",
}

# The locale of the library for each language of the application, and the translations it lacks.
LIBRARY_LOCALES = {
    "en": "en",
    "ru": "ru",
    "es": "es",
    "pt": "pt_br",
    "de": "de-de",
    "zh": "zh_cn",
    "ja": "ja",
}
MISSING_TRANSLATIONS = {"ru": RUSSIAN, "zh": CHINESE, "pt": {"OK": "OK"}}


def library_translation(language: str, text: str) -> str | None:
    """How a text of a library dialog reads in a language: what the application adds, or else
    what the library has; None where there is none."""
    added = MISSING_TRANSLATIONS.get(language, {})
    if text in added:
        return added[text]
    locale = normalize_locale(LIBRARY_LOCALES[language])
    for messages in msgs.MESSAGES:
        if normalize_locale(messages.locale) == locale:
            return dict(messages.messages).get(text)
    return None


def apply_library_locale(language: str) -> None:
    """Make the dialogs of the library speak the language; needs a window to exist."""
    locale = LIBRARY_LOCALES[language]
    for source, translated in MISSING_TRANSLATIONS.get(language, {}).items():
        MessageCatalog.set(locale, source, translated)
    MessageCatalog.locale(locale)

"""The texts of the user interface, in the language the user chose.

Every text is a key of the catalog of a language, `locales/<code>.json`; `t(key)` gives the text
in the language in force, or the English one when that language lacks the key. A new language
is a new catalog with the keys and the `{placeholders}` of the English one (a test checks it).
"""

import json
from importlib import resources

from timer.storage.settings_rules import LANGUAGE_IDS

DEFAULT_LANGUAGE = "en"


def catalog_of(code: str) -> dict[str, str]:
    """The texts of a language, as written in its file."""
    text = (resources.files("timer") / "locales" / f"{code}.json").read_text(encoding="utf-8")
    return json.loads(text)


ENGLISH: dict[str, str] = catalog_of(DEFAULT_LANGUAGE)
CATALOG: dict[str, str] = ENGLISH  # the texts of the language in force
_language = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    """Put the texts of the interface into a language; the language stays if it is unknown."""
    global CATALOG, _language
    if code not in LANGUAGE_IDS:
        raise ValueError(f"unknown language: {code!r}")
    CATALOG = ENGLISH if code == DEFAULT_LANGUAGE else catalog_of(code)
    _language = code


def current_language() -> str:
    return _language


def language_name(code: str) -> str:
    """The name of a language in that language, as the list of languages shows it."""
    return catalog_of(code)["language.name"]


def t(key: str, **values) -> str:
    text = CATALOG[key] if key in CATALOG else ENGLISH[key]
    return text.format(**values)

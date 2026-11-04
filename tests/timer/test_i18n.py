import re
import string

import pytest
from timer import i18n
from timer.i18n import t
from timer.storage.settings_rules import LANGUAGE_IDS


def test_t_returns_text_from_the_catalog(monkeypatch):
    monkeypatch.setattr(i18n, "CATALOG", {"greeting.hello": "Hello"})

    assert t("greeting.hello") == "Hello"


def test_t_substitutes_placeholders(monkeypatch):
    monkeypatch.setattr(i18n, "CATALOG", {"running.session": "Session {n} of {total}"})

    assert t("running.session", n=3, total=6) == "Session 3 of 6"


def test_unknown_key_raises_key_error(monkeypatch):
    monkeypatch.setattr(i18n, "CATALOG", {"greeting.hello": "Hello"})

    with pytest.raises(KeyError):
        t("greeting.helo")


def test_missing_placeholder_value_raises_key_error(monkeypatch):
    monkeypatch.setattr(i18n, "CATALOG", {"running.session": "Session {n}"})

    with pytest.raises(KeyError):
        t("running.session")


def test_english_catalog_is_loaded():
    assert t("app.title") == "Timer"


def test_english_catalog_keys_are_flat_dotted_and_texts_are_not_empty():
    key_format = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")

    assert i18n.CATALOG
    for key, text in i18n.CATALOG.items():
        assert key_format.match(key), f"bad key: {key!r}"
        assert isinstance(text, str) and text.strip(), f"empty text for {key!r}"


# --- the language --------------------------------------------------------------------

PLACEHOLDER_FORMATTER = string.Formatter()


def placeholders_of(text):
    return {name for _, name, _, _ in PLACEHOLDER_FORMATTER.parse(text) if name}


def test_english_is_the_language_at_first():
    assert i18n.current_language() == "en"


def test_a_chosen_language_is_the_one_the_texts_come_in():
    i18n.set_language("ru")

    assert i18n.current_language() == "ru"
    assert t("nav.back") == "Назад"


def test_the_language_can_be_changed_back():
    i18n.set_language("ru")
    i18n.set_language("en")

    assert t("nav.back") == "Back"


def test_an_unknown_language_is_refused_and_the_language_stays():
    with pytest.raises(ValueError):
        i18n.set_language("xx")

    assert i18n.current_language() == "en"


def test_a_text_the_language_lacks_is_shown_in_english(monkeypatch):
    i18n.set_language("ru")
    monkeypatch.setattr(i18n, "CATALOG", {})

    assert t("nav.back") == "Back"


def test_a_key_that_no_language_has_still_raises_key_error():
    i18n.set_language("ru")

    with pytest.raises(KeyError):
        t("nav.nonsense")


@pytest.mark.parametrize(("code", "name"), [("en", "English"), ("ru", "Русский")])
def test_a_language_is_named_in_itself(code, name):
    assert i18n.language_name(code) == name


def test_the_name_of_a_language_does_not_depend_on_the_language_in_force():
    i18n.set_language("ru")

    assert i18n.language_name("en") == "English"


@pytest.mark.parametrize("code", LANGUAGE_IDS)
def test_a_catalog_has_the_keys_of_the_english_one_and_no_others(code):
    english = i18n.catalog_of("en")
    catalog = i18n.catalog_of(code)

    assert set(catalog) == set(english)


@pytest.mark.parametrize("code", LANGUAGE_IDS)
def test_a_catalog_has_the_placeholders_of_the_english_one(code):
    english = i18n.catalog_of("en")
    catalog = i18n.catalog_of(code)

    for key, text in english.items():
        assert placeholders_of(catalog[key]) == placeholders_of(text), key


@pytest.mark.parametrize("code", LANGUAGE_IDS)
def test_every_text_of_a_catalog_is_filled_and_every_key_well_formed(code):
    key_format = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")

    for key, text in i18n.catalog_of(code).items():
        assert key_format.match(key), f"bad key: {key!r}"
        assert isinstance(text, str) and text.strip(), f"empty text for {key!r}"


@pytest.mark.parametrize("code", LANGUAGE_IDS)
def test_a_catalog_has_its_own_name_and_the_texts_of_the_dialogs(code):
    catalog = i18n.catalog_of(code)

    assert catalog["language.name"]
    assert catalog["dialog.yes"] and catalog["dialog.no"]

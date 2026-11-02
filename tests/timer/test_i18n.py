import re

import pytest
from timer import i18n
from timer.i18n import t


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

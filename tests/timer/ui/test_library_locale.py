import pytest
from timer.storage.settings_rules import LANGUAGE_IDS
from timer.ui.library_locale import (
    LIBRARY_LOCALES,
    LIBRARY_STRINGS_USED,
    RUSSIAN,
    library_translation,
)

OTHER_LANGUAGES = [code for code in LANGUAGE_IDS if code != "en"]


def test_every_text_of_the_library_dialogs_we_use_has_a_russian_translation():
    for text in LIBRARY_STRINGS_USED:
        assert RUSSIAN.get(text), text


def test_every_language_has_a_locale_of_the_library():
    assert set(LIBRARY_LOCALES) == set(LANGUAGE_IDS)


@pytest.mark.parametrize("code", OTHER_LANGUAGES)
def test_every_text_of_the_library_dialogs_we_use_is_translated_in_every_language(code):
    for text in LIBRARY_STRINGS_USED:
        assert library_translation(code, text), (code, text)


@pytest.mark.parametrize("code", OTHER_LANGUAGES)
@pytest.mark.parametrize("text", ["Cancel", "Submit", "Hue"])
def test_a_translation_of_the_library_is_not_the_english_text_itself(code, text):
    assert library_translation(code, text) != text

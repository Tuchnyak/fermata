from timer.ui.library_locale import LIBRARY_STRINGS_USED, RUSSIAN


def test_every_text_of_the_library_dialogs_we_use_has_a_russian_translation():
    for text in LIBRARY_STRINGS_USED:
        assert RUSSIAN.get(text), text

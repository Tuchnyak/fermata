import pytest
from timer.i18n import t
from timer.storage.settings_rules import THEME_IDS
from timer.themes import DEFAULT_THEME, definition_of, register_themes, ttk_theme_name

LIGHT_THEMES = {"light", "catppuccin_latte"}


def luminance(color: str) -> float:
    channels = []
    for start in (1, 3, 5):
        value = int(color[start : start + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    """The WCAG contrast ratio of two colors: 1 (none) to 21 (black on white)."""
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# --- the themes --------------------------------------------------------------------


def test_there_are_six_themes():
    assert THEME_IDS == (
        "light",
        "dark",
        "catppuccin_latte",
        "catppuccin_frappe",
        "catppuccin_macchiato",
        "catppuccin_mocha",
    )


def test_dark_is_the_default_theme():
    assert DEFAULT_THEME == "dark"


def test_every_theme_is_defined_under_its_own_name():
    names = [definition_of(theme_id).name for theme_id in THEME_IDS]

    assert len(set(names)) == len(THEME_IDS)


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_a_theme_is_light_or_dark_as_its_name_says(theme_id):
    expected = "light" if theme_id in LIGHT_THEMES else "dark"

    assert definition_of(theme_id).mode == expected


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_ttkbootstrap_knows_a_theme_by_the_name_of_its_definition(theme_id):
    assert ttk_theme_name(theme_id) == definition_of(theme_id).name


@pytest.mark.parametrize("unknown", ["", "nonsense", None, "Dark"])
def test_an_unknown_theme_is_the_default_one(unknown):
    assert ttk_theme_name(unknown) == ttk_theme_name(DEFAULT_THEME)


def test_registering_the_themes_before_a_window_exists_is_allowed():
    register_themes()


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_every_theme_has_a_name_in_the_catalog(theme_id):
    assert t(f"theme.{theme_id}")


# --- readability -------------------------------------------------------------------


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_text_is_readable_on_the_background(theme_id):
    colors = definition_of(theme_id).colors

    assert contrast(colors.fg, colors.bg) >= 4.5


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_text_is_readable_in_input_fields(theme_id):
    colors = definition_of(theme_id).colors

    assert contrast(colors.inputfg, colors.inputbg) >= 4.5


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_messages_in_the_success_and_danger_colors_are_readable_on_the_background(theme_id):
    colors = definition_of(theme_id).colors

    assert contrast(colors.success, colors.bg) >= 4.0
    assert contrast(colors.danger, colors.bg) >= 4.0


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_selected_text_stands_out_from_its_highlight(theme_id):
    colors = definition_of(theme_id).colors

    assert contrast(colors.selectfg, colors.selectbg) >= 3.0

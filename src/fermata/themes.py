"""The themes of the application: the palettes of the six themes the user can choose.

A theme is a ttkbootstrap `Theme`: a few accent colors, a background and a foreground, from
which it generates the full set of colors. The ids are those stored in the setting `theme`.
The Catppuccin palettes are the official ones (https://catppuccin.com/palette); Light and Dark
are the application's own.
"""

from ttkbootstrap import Theme
from ttkbootstrap.style.theme import ThemeDefinition

from fermata.storage.settings_rules import THEME_IDS

DEFAULT_THEME = "dark"

_FAMILIES = {
    "light": Theme(
        name="timer-light",
        primary="#0d6efd",
        success="#198754",
        info="#0dcaf0",
        warning="#ffc107",
        danger="#dc3545",
        neutral="#6c757d",
        light=dict(background="#ffffff", foreground="#212529"),
    ),
    "dark": Theme(
        name="timer-dark",
        primary="#375a7f",
        success="#00bc8c",
        info="#3498db",
        warning="#f39c12",
        danger="#e74c3c",
        neutral="#444444",
        dark=dict(background="#222222", foreground="#ffffff"),
    ),
    "catppuccin_latte": Theme(
        name="timer-catppuccin_latte",
        primary="#1e66f5",
        success="#40a02b",
        info="#209fb5",
        warning="#df8e1d",
        danger="#d20f39",
        neutral="#8c8fa1",
        light=dict(background="#eff1f5", foreground="#4c4f69"),
    ),
    "catppuccin_frappe": Theme(
        name="timer-catppuccin_frappe",
        primary="#8caaee",
        success="#a6d189",
        info="#85c1dc",
        warning="#e5c890",
        danger="#e78284",
        neutral="#737994",
        dark=dict(background="#303446", foreground="#c6d0f5"),
    ),
    "catppuccin_macchiato": Theme(
        name="timer-catppuccin_macchiato",
        primary="#8aadf4",
        success="#a6da95",
        info="#7dc4e4",
        warning="#eed49f",
        danger="#ed8796",
        neutral="#6e738d",
        dark=dict(background="#24273a", foreground="#cad3f5"),
    ),
    "catppuccin_mocha": Theme(
        name="timer-catppuccin_mocha",
        primary="#89b4fa",
        success="#a6e3a1",
        info="#74c7ec",
        warning="#f9e2af",
        danger="#f38ba8",
        neutral="#6c7086",
        dark=dict(background="#1e1e2e", foreground="#cdd6f4"),
    ),
}
assert set(_FAMILIES) == set(THEME_IDS)

_DEFINITIONS = {}
for _theme_id, _family in _FAMILIES.items():
    (_DEFINITIONS[_theme_id],) = _family.to_definitions()  # each family has a single mode


def definition_of(theme_id: str) -> ThemeDefinition:
    return _DEFINITIONS[theme_id]


def ttk_theme_name(theme_id: str | None) -> str:
    """The name ttkbootstrap knows the theme by; an unknown or empty id gives the default."""
    if theme_id not in _DEFINITIONS:
        theme_id = DEFAULT_THEME
    return _DEFINITIONS[theme_id].name


def register_themes() -> None:
    """Make the themes known to ttkbootstrap; to be called before the window is created."""
    for family in _FAMILIES.values():
        family.register()

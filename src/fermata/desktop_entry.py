"""The entry of the program in the application menu (a freedesktop `.desktop` file).

The name is the same in every language; the generic name and the line under it come from the
catalogs. `python -m fermata.desktop_entry <executable>` prints the entry, which the install
script writes into the menu.
"""

import sys

from fermata.i18n import catalog_of
from fermata.storage.settings_rules import LANGUAGE_IDS

# The locale names of the menu for the languages that the program names by language only.
MENU_LOCALES = {"pt": "pt_BR", "zh": "zh_CN"}


def desktop_entry(executable: str) -> str:
    english = catalog_of("en")
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={english['app.title']}",
        f"GenericName={english['app.generic_name']}",
        f"Comment={english['app.description']}",
    ]
    for code in LANGUAGE_IDS:
        if code == "en":
            continue
        catalog = catalog_of(code)
        locale = MENU_LOCALES.get(code, code)
        lines.append(f"GenericName[{locale}]={catalog['app.generic_name']}")
        lines.append(f"Comment[{locale}]={catalog['app.description']}")
    lines += [f"Exec={executable}", "Terminal=false", "Categories=Utility;"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(desktop_entry(sys.argv[1]), end="")

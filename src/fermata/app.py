import ttkbootstrap as ttk
from fermata.arguments import parse_arguments
from fermata.build import is_release
from fermata.clock import make_clock, speed_of
from fermata.i18n import current_language, t
from fermata.resume import Resumption
from fermata.storage.paths import db_path
from fermata.themes import register_themes, ttk_theme_name
from fermata.ui.fullscreen import Fullscreen
from fermata.ui.hotkeys import HotkeyHandler
from fermata.ui.library_locale import apply_library_locale
from fermata.ui.main_window import MainWindow
from fermata.ui.navigation import Navigation
from fermata.wiring import build_components
from ttkbootstrap.dialogs import Messagebox

ASK_DELAY_MILLISECONDS = 100  # the window is shown first, the question opens over it


def ask_to_resume(root: ttk.Window, resumption: Resumption) -> None:
    answer = Messagebox.yesno(
        message=resumption.question(),
        title=t("resume.title"),
        parent=root,
        buttons=[t("dialog.no"), t("dialog.yes")],
        localize=False,
    )
    # Closing the question without an answer leaves the session to be offered again.
    if answer == t("dialog.yes"):
        resumption.resume()
    elif answer == t("dialog.no"):
        resumption.decline()


def main():
    arguments = parse_arguments(release=is_release())
    clock = make_clock(release=is_release(), real_time=arguments.real_time)
    components = build_components(db_path(), clock)

    register_themes()
    stored_theme = components.settings_view_model.settings().theme
    root = ttk.Window(themename=ttk_theme_name(stored_theme))
    apply_library_locale(current_language())
    navigation = Navigation()
    fullscreen = Fullscreen()
    hotkey_handler = HotkeyHandler(
        components.engine,
        navigation,
        start_flow=components.home_view_model.start,
        fullscreen=fullscreen,
    )
    MainWindow(
        root,
        navigation,
        hotkey_handler,
        components.categories_view_model,
        components.settings_view_model,
        components.home_view_model,
        components.running_view_model,
        components.waiting_view_model,
        components.scenarios_view_model,
        components.history_view_model,
        fullscreen,
        components.background_sound,
        speed_of(release=is_release(), real_time=arguments.real_time),
    )
    if components.resumption is not None:
        root.after(ASK_DELAY_MILLISECONDS, ask_to_resume, root, components.resumption)
    root.mainloop()

import ttkbootstrap as ttk
from timer.arguments import parse_arguments
from timer.build import is_release
from timer.clock import make_clock, speed_of
from timer.i18n import t
from timer.resume import Resumption
from timer.storage.paths import db_path
from timer.themes import register_themes, ttk_theme_name
from timer.ui.fullscreen import Fullscreen
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow, window_title
from timer.ui.navigation import Navigation
from timer.wiring import build_components
from ttkbootstrap.dialogs import Messagebox

ASK_DELAY_MILLISECONDS = 100  # the window is shown first, the question opens over it


def ask_to_resume(root: ttk.Window, resumption: Resumption) -> None:
    answer = Messagebox.yesno(
        message=resumption.question(),
        title=t("resume.title"),
        parent=root,
        localize=False,
    )
    # Closing the question without an answer leaves the session to be offered again.
    if answer == "Yes":
        resumption.resume()
    elif answer == "No":
        resumption.decline()


def main():
    arguments = parse_arguments(release=is_release())
    clock = make_clock(release=is_release(), real_time=arguments.real_time)
    components = build_components(db_path(), clock)

    register_themes()
    stored_theme = components.settings_view_model.settings().theme
    root = ttk.Window(themename=ttk_theme_name(stored_theme))
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
        fullscreen,
    )
    speed = speed_of(release=is_release(), real_time=arguments.real_time)
    root.title(window_title(speed))
    if components.resumption is not None:
        root.after(ASK_DELAY_MILLISECONDS, ask_to_resume, root, components.resumption)
    root.mainloop()

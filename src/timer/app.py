from datetime import UTC, datetime

import ttkbootstrap as ttk
from timer.i18n import t
from timer.resume import Resumption
from timer.storage.paths import db_path
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow
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
    components = build_components(db_path(), clock=lambda: datetime.now(UTC))

    root = ttk.Window(themename="darkly")
    navigation = Navigation()
    hotkey_handler = HotkeyHandler(
        components.engine, navigation, start_flow=components.home_view_model.start
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
    )
    if components.resumption is not None:
        root.after(ASK_DELAY_MILLISECONDS, ask_to_resume, root, components.resumption)
    root.mainloop()

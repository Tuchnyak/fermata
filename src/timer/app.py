from datetime import UTC, datetime

import ttkbootstrap as ttk
from timer.storage.paths import db_path
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow
from timer.ui.navigation import Navigation
from timer.wiring import build_components


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
    )
    root.mainloop()

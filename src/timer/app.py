from datetime import UTC, datetime

import ttkbootstrap as ttk
from timer.engine import Engine
from timer.storage.settings import Settings
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow
from timer.ui.navigation import Navigation


def main():
    root = ttk.Window(themename="darkly")
    navigation = Navigation()
    engine = Engine(get_settings=Settings, clock=lambda: datetime.now(UTC))
    # Temporary wiring: the database arrives in 1.30 and the home screen supplies the start
    # of a flow in 1.27.
    hotkey_handler = HotkeyHandler(engine, navigation, start_flow=lambda: None)
    MainWindow(root, navigation, hotkey_handler)
    root.mainloop()

from datetime import UTC, datetime

import ttkbootstrap as ttk
from timer.engine import Engine
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.paths import db_path
from timer.storage.settings import Settings
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow
from timer.ui.navigation import Navigation


def main():
    db = Db.open(db_path())
    migrate(db, MIGRATIONS_DIR)

    root = ttk.Window(themename="darkly")
    navigation = Navigation()
    engine = Engine(get_settings=Settings, clock=lambda: datetime.now(UTC))
    # Temporary wiring: the engine reads the default settings and has no recorder yet (1.30),
    # and the home screen supplies the start of a flow in 1.27.
    hotkey_handler = HotkeyHandler(engine, navigation, start_flow=lambda: None)
    categories_view_model = CategoriesViewModel(CategoryRepository(db))
    MainWindow(root, navigation, hotkey_handler, categories_view_model)
    root.mainloop()

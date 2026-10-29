from datetime import UTC, datetime

import ttkbootstrap as ttk
from timer.engine import Engine
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.paths import db_path
from timer.storage.sessions import SessionRepository
from timer.storage.settings import Settings, SettingsRepository
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.home_view_model import HomeViewModel
from timer.ui.hotkeys import HotkeyHandler
from timer.ui.main_window import MainWindow
from timer.ui.navigation import Navigation
from timer.ui.running_view_model import RunningViewModel
from timer.ui.settings_view_model import SettingsViewModel


def main():
    db = Db.open(db_path())
    migrate(db, MIGRATIONS_DIR)

    root = ttk.Window(themename="darkly")
    navigation = Navigation()
    category_repository = CategoryRepository(db)
    # Temporary wiring: the engine reads the default settings and has no recorder yet (1.30).
    engine = Engine(get_settings=Settings, clock=lambda: datetime.now(UTC))
    home_view_model = HomeViewModel(category_repository, SessionRepository(db), engine)
    hotkey_handler = HotkeyHandler(engine, navigation, start_flow=home_view_model.start)
    MainWindow(
        root,
        navigation,
        hotkey_handler,
        CategoriesViewModel(category_repository),
        SettingsViewModel(SettingsRepository(db)),
        home_view_model,
        RunningViewModel(engine, category_repository),
    )
    root.mainloop()

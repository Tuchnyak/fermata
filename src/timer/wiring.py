"""Builds the parts of the application that need no Tk: database, engine, view models.

Startup recovery runs before the engine exists, so what a closed window left running is
marked interrupted before anything new is recorded.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from timer.engine import Engine
from timer.recorder import Recorder
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.sessions import SessionRepository
from timer.storage.settings import SettingsRepository
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.home_view_model import HomeViewModel
from timer.ui.running_view_model import RunningViewModel
from timer.ui.settings_view_model import SettingsViewModel


@dataclass(frozen=True)
class Components:
    engine: Engine
    categories_view_model: CategoriesViewModel
    settings_view_model: SettingsViewModel
    home_view_model: HomeViewModel
    running_view_model: RunningViewModel


def build_components(
    database_path: str | Path, clock: Callable[[], datetime]
) -> Components:
    db = Db.open(database_path)
    migrate(db, MIGRATIONS_DIR)
    category_repository = CategoryRepository(db)
    settings_repository = SettingsRepository(db)
    session_repository = SessionRepository(db)

    session_repository.interrupt_running_sessions()

    recorder = Recorder(db, session_repository)
    engine = Engine(
        get_settings=settings_repository.get_all,
        clock=clock,
        on_flow_event=recorder.record,
    )
    return Components(
        engine=engine,
        categories_view_model=CategoriesViewModel(category_repository),
        settings_view_model=SettingsViewModel(settings_repository),
        home_view_model=HomeViewModel(category_repository, session_repository, engine),
        running_view_model=RunningViewModel(engine, category_repository),
    )

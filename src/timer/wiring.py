"""Builds the parts of the application that need no Tk: database, engine, view models.

Startup recovery runs before the engine exists, so what a closed window left running is
marked interrupted before anything new is recorded; a scenario session it left behind is
offered for resuming.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from timer.engine import Engine
from timer.recorder import Recorder
from timer.resume import Resumption
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.scenarios import ScenarioRepository
from timer.storage.sessions import SessionRepository
from timer.storage.settings import SettingsRepository
from timer.ui.categories_view_model import CategoriesViewModel
from timer.ui.home_view_model import HomeViewModel
from timer.ui.running_view_model import RunningViewModel
from timer.ui.scenarios_view_model import ScenariosViewModel
from timer.ui.settings_view_model import SettingsViewModel
from timer.ui.waiting_view_model import WaitingViewModel


@dataclass(frozen=True)
class Components:
    engine: Engine
    categories_view_model: CategoriesViewModel
    settings_view_model: SettingsViewModel
    home_view_model: HomeViewModel
    running_view_model: RunningViewModel
    waiting_view_model: WaitingViewModel
    scenarios_view_model: ScenariosViewModel
    resumption: Resumption | None  # set when a scenario session is left to resume


def build_components(
    database_path: str | Path, clock: Callable[[], datetime]
) -> Components:
    db = Db.open(database_path)
    migrate(db, MIGRATIONS_DIR)
    category_repository = CategoryRepository(db)
    settings_repository = SettingsRepository(db)
    session_repository = SessionRepository(db)
    scenario_repository = ScenarioRepository(db)

    session_repository.interrupt_running_sessions()

    recorder = Recorder(db, session_repository)
    engine = Engine(
        get_settings=settings_repository.get_all,
        clock=clock,
        on_flow_event=recorder.record,
    )
    interrupted = session_repository.latest_interrupted_scenario_session()
    resumption = None
    if interrupted is not None:
        resumption = Resumption(session_repository, recorder, engine, interrupted)
    return Components(
        engine=engine,
        categories_view_model=CategoriesViewModel(category_repository),
        settings_view_model=SettingsViewModel(settings_repository),
        home_view_model=HomeViewModel(
            category_repository, session_repository, engine, scenario_repository
        ),
        running_view_model=RunningViewModel(
            engine, category_repository, settings_repository
        ),
        waiting_view_model=WaitingViewModel(engine),
        scenarios_view_model=ScenariosViewModel(
            scenario_repository, category_repository, settings_repository, engine
        ),
        resumption=resumption,
    )

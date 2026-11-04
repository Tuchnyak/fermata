"""Builds the parts of the application that need no Tk: database, engine, view models.

Startup recovery runs before the engine exists, so what a closed window left running is
marked interrupted before anything new is recorded; a scenario session it left behind is
offered for resuming.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fermata.background_sound import BackgroundSound
from fermata.engine import Engine, FlowEvent
from fermata.i18n import set_language
from fermata.recorder import Recorder
from fermata.resume import Resumption
from fermata.sound import SOUNDS_DIR, SoundNotifier, SoundPlayer
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.history import HistoryRepository
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.scenarios import ScenarioRepository
from fermata.storage.sessions import SessionRepository
from fermata.storage.settings import SettingsRepository
from fermata.ui.categories_view_model import CategoriesViewModel
from fermata.ui.history_view_model import HistoryViewModel
from fermata.ui.home_view_model import HomeViewModel
from fermata.ui.running_view_model import RunningViewModel
from fermata.ui.scenarios_view_model import ScenariosViewModel
from fermata.ui.settings_view_model import SettingsViewModel
from fermata.ui.waiting_view_model import WaitingViewModel


@dataclass(frozen=True)
class Components:
    engine: Engine
    background_sound: BackgroundSound
    categories_view_model: CategoriesViewModel
    settings_view_model: SettingsViewModel
    home_view_model: HomeViewModel
    running_view_model: RunningViewModel
    waiting_view_model: WaitingViewModel
    scenarios_view_model: ScenariosViewModel
    history_view_model: HistoryViewModel
    resumption: Resumption | None  # set when a scenario session is left to resume


def _broadcast(*listeners: Callable[[FlowEvent], None]) -> Callable[[FlowEvent], None]:
    """One listener that hands each event to all the given ones, in order."""

    def listener(event: FlowEvent) -> None:
        for each in listeners:
            each(event)

    return listener


def build_components(
    database_path: str | Path,
    clock: Callable[[], datetime],
    sound_player: SoundPlayer | None = None,
) -> Components:
    db = Db.open(database_path)
    migrate(db, MIGRATIONS_DIR)
    category_repository = CategoryRepository(db)
    settings_repository = SettingsRepository(db)
    session_repository = SessionRepository(db)
    scenario_repository = ScenarioRepository(db)

    set_language(settings_repository.get_all().language)
    session_repository.interrupt_running_sessions()

    recorder = Recorder(db, session_repository)
    notifier = SoundNotifier(
        settings_repository.get_all, sound_player or SoundPlayer(SOUNDS_DIR)
    )
    engine = Engine(
        get_settings=settings_repository.get_all,
        clock=clock,
        on_flow_event=_broadcast(recorder.record, notifier),
    )
    interrupted = session_repository.latest_interrupted_scenario_session()
    resumption = None
    if interrupted is not None:
        resumption = Resumption(session_repository, recorder, engine, interrupted)
    return Components(
        engine=engine,
        background_sound=BackgroundSound(
            engine, settings_repository.get_all, SOUNDS_DIR
        ),
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
        history_view_model=HistoryViewModel(HistoryRepository(db), clock),
        resumption=resumption,
    )

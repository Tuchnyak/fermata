"""What the scenarios screen shows and does, without any Tk: the list, starting and deleting."""

from timer.engine import Engine
from timer.scenarios import ScenarioEntity
from timer.storage.categories import CategoryRepository
from timer.storage.scenarios import ScenarioRepository
from timer.storage.settings import SettingsRepository
from timer.ui.scenario_editor_view_model import ScenarioEditorViewModel
from timer.ui.scenario_summary import describe


class ScenariosViewModel:
    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        category_repository: CategoryRepository,
        settings_repository: SettingsRepository,
        engine: Engine,
    ):
        self._scenario_repository = scenario_repository
        self._category_repository = category_repository
        self._settings_repository = settings_repository
        self._engine = engine

    def scenarios(self) -> list[ScenarioEntity]:
        return self._scenario_repository.list_all()

    def describe(self, scenario: ScenarioEntity) -> str:
        work_count = len(scenario.work_category_ids())
        total_seconds = scenario.total_seconds(self._settings_repository.get_all())
        return describe(work_count, total_seconds)

    def can_start(self) -> bool:
        """Only one session runs at a time."""
        return (
            self._engine.current_interval is None
            and self._engine.upcoming_interval is None
        )

    def start(self, scenario_id: int) -> None:
        if not self.can_start():
            return
        scenario = self._scenario_repository.get_by_id(scenario_id)
        if scenario is None:
            raise LookupError(f"No scenario with id {scenario_id}")
        self._engine.start_scenario(scenario)

    def delete(self, scenario_id: int) -> None:
        self._scenario_repository.delete(scenario_id)

    def new_editor(self) -> ScenarioEditorViewModel:
        return ScenarioEditorViewModel(
            self._scenario_repository,
            self._category_repository,
            self._settings_repository,
        )

    def editor_for(self, scenario_id: int) -> ScenarioEditorViewModel:
        scenario = self._scenario_repository.get_by_id(scenario_id)
        if scenario is None:
            raise LookupError(f"No scenario with id {scenario_id}")
        return ScenarioEditorViewModel(
            self._scenario_repository,
            self._category_repository,
            self._settings_repository,
            scenario,
        )

"""What the home screen shows and does, without any Tk: the category to start a flow with."""

from enum import Enum, auto

from timer.engine import Engine
from timer.i18n import t
from timer.scenarios import ScenarioEntity
from timer.storage.categories import Category, CategoryRepository
from timer.storage.scenarios import ScenarioRepository
from timer.storage.sessions import SessionRepository


class HomeMode(Enum):
    IDLE = auto()
    RUNNING = auto()
    WAITING = auto()


class StartKind(Enum):
    FLOW = auto()
    SCENARIO = auto()


class HomeViewModel:
    def __init__(
        self,
        category_repository: CategoryRepository,
        session_repository: SessionRepository,
        engine: Engine,
        scenario_repository: ScenarioRepository,
    ):
        self._category_repository = category_repository
        self._session_repository = session_repository
        self._engine = engine
        self._scenario_repository = scenario_repository
        self._start_kind = StartKind.FLOW
        self._selected_scenario_id: int | None = None
        self._selected_category_id = self._preselected_category_id()

    def start_kind(self) -> StartKind:
        if self._start_kind == StartKind.SCENARIO and not self.scenarios():
            return StartKind.FLOW  # the scenarios have been deleted since
        return self._start_kind

    def select_start_kind(self, kind: StartKind) -> None:
        if kind == StartKind.SCENARIO and not self.scenarios():
            return
        self._start_kind = kind

    def scenarios(self) -> list[ScenarioEntity]:
        return self._scenario_repository.list_all()

    def selected_scenario(self) -> ScenarioEntity | None:
        """The scenario chosen, or the first one if it was deleted or none was chosen."""
        scenarios = self.scenarios()
        for scenario in scenarios:
            if scenario.id == self._selected_scenario_id:
                return scenario
        return scenarios[0] if scenarios else None

    def select_scenario(self, scenario_id: int) -> None:
        self._selected_scenario_id = scenario_id

    def summary_text(self) -> str | None:
        """How the last scenario session went, until the next session starts."""
        summary = self._engine.summary()
        scenario = self._engine.scenario
        if summary is None or scenario is None:
            return None
        return t(
            "home.summary",
            name=scenario.name,
            done=summary.done_count,
            skipped=summary.skipped_count,
        )

    def mode(self) -> HomeMode:
        if self._engine.current_interval is not None:
            return HomeMode.RUNNING
        if self._engine.upcoming_interval is not None:
            return HomeMode.WAITING
        return HomeMode.IDLE

    def categories(self) -> list[Category]:
        return self._category_repository.list_active()

    def selected_category(self) -> Category:
        category = self._category_repository.get_by_id(self._selected_category_id)
        assert category is not None
        return category

    def select(self, category_id: int) -> None:
        self._selected_category_id = category_id

    def preselect(self) -> None:
        """Select the category of the previous flow, as the home screen is shown again."""
        self._selected_category_id = self._preselected_category_id()

    def start(self) -> None:
        if self.start_kind() == StartKind.SCENARIO:
            scenario = self.selected_scenario()
            assert scenario is not None
            self._engine.start_scenario(scenario)
        else:
            self._engine.start_flow(self._selected_category_id)

    def _preselected_category_id(self) -> int:
        """The category of the previous flow if it is still active, otherwise `None`."""
        active_categories = self.categories()
        previous_category_id = self._session_repository.last_flow_category_id()
        for category in active_categories:
            if category.id == previous_category_id:
                return category.id
        system_category = next(
            category for category in active_categories if category.is_system
        )
        return system_category.id

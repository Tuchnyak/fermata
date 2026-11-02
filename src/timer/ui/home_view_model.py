"""What the home screen shows and does, without any Tk: the category to start a flow with."""

from enum import Enum, auto

from timer.engine import Engine
from timer.storage.categories import Category, CategoryRepository
from timer.storage.sessions import SessionRepository


class HomeMode(Enum):
    IDLE = auto()
    RUNNING = auto()
    WAITING = auto()


class HomeViewModel:
    def __init__(
        self,
        category_repository: CategoryRepository,
        session_repository: SessionRepository,
        engine: Engine,
    ):
        self._category_repository = category_repository
        self._session_repository = session_repository
        self._engine = engine
        self._selected_category_id = self._preselected_category_id()

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

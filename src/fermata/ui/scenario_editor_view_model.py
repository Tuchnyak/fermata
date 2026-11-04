"""What the scenario editor shows and does, without any Tk: a draft of the scenario being edited,
its live preview and saving.

Nothing is stored until `save`. Numbers arrive as the text typed into the form; text that is
not a whole number is remembered as None, which blanks the preview and is refused on save.
"""

from dataclasses import dataclass

from fermata.i18n import t
from fermata.scenarios import (
    OVERRIDE_FIELDS,
    REPEAT_COUNT_RANGE,
    ROW_COUNT_RANGE,
    Scenario,
    ScenarioEntity,
    ScenarioRow,
)
from fermata.storage.categories import Category, CategoryRepository
from fermata.storage.scenarios import ScenarioRepository
from fermata.storage.settings import Settings, SettingsRepository
from fermata.ui.progress import CircleState, ProgressItem, progress_items
from fermata.ui.scenario_summary import describe
from fermata.validation import ValidationError


@dataclass
class RowDraft:
    category_id: int
    count: int | None  # None: what was typed is not a whole number


@dataclass(frozen=True)
class Preview:
    items: list[ProgressItem]
    work_count: int
    text: str


def _to_number(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def _is_within(value: int, limits: tuple[int, int]) -> bool:
    lowest, highest = limits
    return lowest <= value <= highest


class ScenarioEditorViewModel:
    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        category_repository: CategoryRepository,
        settings_repository: SettingsRepository,
        scenario: ScenarioEntity | None = None,
    ):
        self._scenario_repository = scenario_repository
        self._category_repository = category_repository
        self._settings_repository = settings_repository
        self.saved_scenario_id: int | None = None
        self._stored_scenario_id = None if scenario is None else scenario.id

        self._overrides: dict[str, int | None] = {}
        if scenario is None:
            self._name = ""
            self._rows = [RowDraft(self.categories()[0].id, 1)]
            self._repeat_count: int | None = 1
            for field_name in OVERRIDE_FIELDS:
                self._overrides[field_name] = None
        else:
            self._name = scenario.name
            self._rows = [RowDraft(row.category_id, row.count) for row in scenario.rows]
            self._repeat_count = scenario.repeat_count
            for field_name in OVERRIDE_FIELDS:
                self._overrides[field_name] = getattr(scenario, field_name)

    def name(self) -> str:
        return self._name

    def set_name(self, text: str) -> None:
        self._name = text

    def categories(self) -> list[Category]:
        return self._category_repository.list_active()

    def rows(self) -> list[RowDraft]:
        return self._rows

    def add_row(self) -> None:
        category_id = self._rows[-1].category_id if self._rows else self.categories()[0].id
        self._rows.append(RowDraft(category_id, 1))

    def remove_row(self, index: int) -> None:
        del self._rows[index]

    def move_row_up(self, index: int) -> None:
        if index > 0:
            self._swap_rows(index - 1, index)

    def move_row_down(self, index: int) -> None:
        if index < len(self._rows) - 1:
            self._swap_rows(index, index + 1)

    def set_row_category(self, index: int, category_id: int) -> None:
        self._rows[index].category_id = category_id

    def set_row_count(self, index: int, text: str) -> None:
        self._rows[index].count = _to_number(text)

    def repeat_count(self) -> int | None:
        return self._repeat_count

    def set_repeat_count(self, text: str) -> None:
        self._repeat_count = _to_number(text)

    def overrides(self) -> dict[str, int | None]:
        return self._overrides

    def set_override(self, field_name: str, value: int | None) -> None:
        if field_name not in self._overrides:
            raise KeyError(field_name)
        self._overrides[field_name] = value

    def global_settings(self) -> Settings:
        return self._settings_repository.get_all()

    def preview(self) -> Preview:
        """The circles, the number of work intervals and the total time of the draft.

        Blank while the draft cannot be shown: no rows, or a number that is not valid.
        """
        scenario = self._draft()
        if scenario is None or not self._numbers_are_within_limits(scenario):
            return Preview([], 0, "")
        category_ids = scenario.work_category_ids()
        if not category_ids:
            return Preview([], 0, "")

        colors = []
        for category_id in category_ids:
            category = self._category_repository.get_by_id(category_id)
            assert category is not None
            colors.append(category.color)
        settings = self.global_settings()
        items = progress_items(
            colors,
            [CircleState.FUTURE] * len(colors),
            scenario.effective_settings(settings).long_break_every,
        )
        text = describe(len(colors), scenario.total_seconds(settings))
        return Preview(items, len(colors), text)

    def save(self) -> str | None:
        """Store the draft; return the message to show if it is rejected, else None."""
        scenario = self._draft()
        if scenario is None:
            return t("scenario.number_invalid")
        try:
            if self._stored_scenario_id is None:
                stored = self._scenario_repository.create(scenario)
            else:
                stored = self._scenario_repository.update(
                    self._stored_scenario_id, scenario
                )
        except ValidationError as error:
            return t(error.key)
        self._stored_scenario_id = stored.id
        self.saved_scenario_id = stored.id
        return None

    def _swap_rows(self, first: int, second: int) -> None:
        self._rows[first], self._rows[second] = self._rows[second], self._rows[first]

    def _draft(self) -> Scenario | None:
        """The draft as a scenario, or None while a number in it is not valid."""
        if self._repeat_count is None:
            return None
        rows = []
        for row in self._rows:
            if row.count is None:
                return None
            rows.append(ScenarioRow(row.category_id, row.count))
        return Scenario(
            self._name, tuple(rows), self._repeat_count, **self._overrides
        )

    def _numbers_are_within_limits(self, scenario: Scenario) -> bool:
        # Keeps the preview from building a list of millions of circles for a typo.
        if not _is_within(scenario.repeat_count, REPEAT_COUNT_RANGE):
            return False
        return all(_is_within(row.count, ROW_COUNT_RANGE) for row in scenario.rows)

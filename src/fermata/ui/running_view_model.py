"""What the running screen shows and does, without any Tk: the title, the work interval number,
the countdown and the buttons."""

import math

from fermata.engine import Engine
from fermata.i18n import t
from fermata.intervals import IntervalKind, IntervalStatus, RunningInterval
from fermata.logic import format_time
from fermata.scenarios import Scenario
from fermata.storage.categories import Category, CategoryRepository
from fermata.storage.settings import SettingsRepository
from fermata.ui.progress import CircleState, ProgressItem, progress_items


class RunningViewModel:
    def __init__(
        self,
        engine: Engine,
        category_repository: CategoryRepository,
        settings_repository: SettingsRepository,
    ):
        self._engine = engine
        self._category_repository = category_repository
        self._settings_repository = settings_repository
        self._colored_scenario: Scenario | None = None
        self._colors: list[str] = []

    def number_text(self) -> str:
        number = self.work_interval_number()
        scenario = self._engine.scenario
        if scenario is None:
            return t("running.work_interval_number", number=number)
        total = len(scenario.work_category_ids())
        return t("running.work_interval_of_total", number=number, total=total)

    def progress_items(self) -> list[ProgressItem] | None:
        """The circle row of a scenario session; None for a flow."""
        scenario = self._engine.scenario
        if scenario is None:
            return None
        colors = self._colors_of(scenario)
        long_break_every = scenario.effective_settings(
            self._settings_repository.get_all()
        ).long_break_every
        return progress_items(colors, self._circle_states(len(colors)), long_break_every)

    def blink(self) -> bool:
        return self._settings_repository.get_all().blink

    def title(self) -> str:
        interval = self._current_interval()
        if interval.kind == IntervalKind.SHORT_BREAK:
            return t("running.short_break")
        if interval.kind == IntervalKind.LONG_BREAK:
            return t("running.long_break")
        return self._category_of(interval).name

    def color(self) -> str | None:
        """The color of the category of a work interval; a break has none."""
        interval = self._current_interval()
        if interval.kind != IntervalKind.WORK:
            return None
        return self._category_of(interval).color

    def work_interval_number(self) -> int:
        """The number of the work interval running now, or just done if a break runs."""
        number = 0
        for finished_interval in self._engine.finished_intervals:
            if finished_interval.kind == IntervalKind.WORK:
                number += 1
        if self._current_interval().kind == IntervalKind.WORK:
            number += 1
        return number

    def countdown(self) -> str:
        # Rounded up: a second that has been started still counts, and 00:00 is shown only
        # when the time is really up.
        return format_time(math.ceil(self._engine.remaining_seconds()))

    def pause_button_text(self) -> str:
        return t("running.resume") if self._engine.is_paused else t("running.pause")

    def tick(self) -> None:
        self._engine.tick()

    def toggle_pause(self) -> None:
        if self._engine.is_paused:
            self._engine.resume()
        else:
            self._engine.pause()

    def skip(self) -> None:
        self._engine.skip()

    def stop(self) -> None:
        self._engine.stop()

    def _colors_of(self, scenario: Scenario) -> list[str]:
        # The categories of a session do not change, so they are looked up once.
        if self._colored_scenario is not scenario:
            colors = []
            for category_id in scenario.work_category_ids():
                category = self._category_repository.get_by_id(category_id)
                assert category is not None
                colors.append(category.color)
            self._colored_scenario = scenario
            self._colors = colors
        return self._colors

    def _circle_states(self, count: int) -> list[CircleState]:
        states = []
        for interval in self._engine.finished_intervals:
            if interval.kind != IntervalKind.WORK:
                continue
            if interval.status == IntervalStatus.COMPLETED:
                states.append(CircleState.DONE)
            else:
                states.append(CircleState.SKIPPED)
        current_interval = self._engine.current_interval
        if current_interval is not None and current_interval.kind == IntervalKind.WORK:
            states.append(CircleState.CURRENT)
        states.extend([CircleState.FUTURE] * (count - len(states)))
        return states

    def _category_of(self, interval: RunningInterval) -> Category:
        assert interval.category_id is not None
        category = self._category_repository.get_by_id(interval.category_id)
        assert category is not None
        return category

    def _current_interval(self) -> RunningInterval:
        interval = self._engine.current_interval
        assert interval is not None
        return interval

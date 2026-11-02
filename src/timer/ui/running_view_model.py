"""What the running screen shows and does, without any Tk: the title, the work interval number,
the countdown and the buttons."""

import math

from timer.engine import Engine
from timer.i18n import t
from timer.intervals import IntervalKind, RunningInterval
from timer.logic import format_time
from timer.storage.categories import Category, CategoryRepository


class RunningViewModel:
    def __init__(self, engine: Engine, category_repository: CategoryRepository):
        self._engine = engine
        self._category_repository = category_repository

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

    def _category_of(self, interval: RunningInterval) -> Category:
        assert interval.category_id is not None
        category = self._category_repository.get_by_id(interval.category_id)
        assert category is not None
        return category

    def _current_interval(self) -> RunningInterval:
        interval = self._engine.current_interval
        assert interval is not None
        return interval

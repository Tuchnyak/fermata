"""What the waiting screen shows and does, without any Tk: what comes next and the buttons."""

from timer.engine import Engine
from timer.i18n import t
from timer.intervals import BaseInterval, IntervalKind


class WaitingViewModel:
    def __init__(self, engine: Engine):
        self._engine = engine

    def next_title(self) -> str:
        interval = self._upcoming_interval()
        if interval.kind == IntervalKind.SHORT_BREAK:
            return t("waiting.next_short_break")
        if interval.kind == IntervalKind.LONG_BREAK:
            return t("waiting.next_long_break")
        number = self._upcoming_work_interval_number()
        scenario = self._engine.scenario
        if scenario is None:
            return t("waiting.next_work", number=number)
        total = len(scenario.work_category_ids())
        return t("waiting.next_work_of_total", number=number, total=total)

    def confirm(self) -> None:
        self._engine.confirm()

    def stop(self) -> None:
        self._engine.stop()

    def _upcoming_work_interval_number(self) -> int:
        number = 1
        for finished_interval in self._engine.finished_intervals:
            if finished_interval.kind == IntervalKind.WORK:
                number += 1
        return number

    def _upcoming_interval(self) -> BaseInterval:
        interval = self._engine.upcoming_interval
        assert interval is not None
        return interval

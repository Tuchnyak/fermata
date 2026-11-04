"""What the history screen shows and does, without any Tk: the period, the list, the totals."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, tzinfo

from fermata.i18n import t
from fermata.logic import format_duration
from fermata.storage.history import HistoryInterval, HistoryRepository
from fermata.ui.history_period import PeriodKind, period_title, shift, utc_bounds, weekday_name


@dataclass(frozen=True)
class HistoryRow:
    color: str
    category: str
    started: str  # `12:30` in a day, `Mon 12:30` in a week
    duration: str  # `25m`, or a dash when it is not known
    status: str


@dataclass(frozen=True)
class CategoryTotal:
    color: str
    category: str
    duration: str


@dataclass(frozen=True)
class HistoryView:
    kind: PeriodKind
    title: str
    rows: list[HistoryRow]
    totals: list[CategoryTotal]
    total: str  # the actual time of the whole period


class HistoryViewModel:
    def __init__(
        self,
        history_repository: HistoryRepository,
        clock: Callable[[], datetime],
        zone: tzinfo | None = None,
    ):
        self._history_repository = history_repository
        self._clock = clock
        self._zone = zone
        self._kind = PeriodKind.DAY
        self._anchor = self._today()

    def show_day(self) -> None:
        self._kind = PeriodKind.DAY

    def show_week(self) -> None:
        self._kind = PeriodKind.WEEK

    def previous(self) -> None:
        self._anchor = shift(self._kind, self._anchor, -1)

    def next(self) -> None:
        self._anchor = shift(self._kind, self._anchor, 1)

    def go_to_today(self) -> None:
        self._anchor = self._today()

    def view(self) -> HistoryView:
        start, end = utc_bounds(self._kind, self._anchor, self._zone)
        intervals = self._history_repository.work_intervals(start, end)
        rows = []
        for interval in intervals:
            rows.append(self._row_of(interval))
        totals, total_seconds = _totals_of(intervals)
        return HistoryView(
            kind=self._kind,
            title=period_title(self._kind, self._anchor),
            rows=rows,
            totals=totals,
            total=format_duration(total_seconds),
        )

    def _today(self) -> date:
        return self._clock().astimezone(self._zone).date()

    def _row_of(self, interval: HistoryInterval) -> HistoryRow:
        started = interval.started_at.astimezone(self._zone)
        time_text = f"{started:%H:%M}"
        if self._kind == PeriodKind.WEEK:
            time_text = t(
                "history.start_in_week", weekday=weekday_name(started), time=time_text
            )
        if interval.actual_seconds is None:
            duration = t("history.no_duration")
        else:
            duration = format_duration(interval.actual_seconds)
        return HistoryRow(
            color=interval.category_color,
            category=interval.category_name,
            started=time_text,
            duration=duration,
            status=t(f"history.status.{interval.status}"),
        )


def _totals_of(intervals: list[HistoryInterval]) -> tuple[list[CategoryTotal], int]:
    """The actual time per category, longest first, and in all. An interval whose length is not
    known adds nothing."""
    seconds_by_category: dict[tuple[str, str], int] = {}
    for interval in intervals:
        if interval.actual_seconds is None:
            continue
        key = (interval.category_name, interval.category_color)
        seconds_by_category[key] = seconds_by_category.get(key, 0) + interval.actual_seconds
    ordered = sorted(seconds_by_category.items(), key=_longest_first)
    totals = []
    for (name, color), seconds in ordered:
        totals.append(CategoryTotal(color, name, format_duration(seconds)))
    return totals, sum(seconds_by_category.values())


def _longest_first(item: tuple[tuple[str, str], int]) -> tuple[int, str]:
    (name, _color), seconds = item
    return (-seconds, name)

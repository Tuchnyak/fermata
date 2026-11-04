"""The period the history screen shows: a day or a week, no Tk.

A period is a kind and an anchor day, any day in it: the previous and the next period move the
anchor, switching the kind keeps it. The bounds are in the local time, the database is in UTC.
"""

from datetime import UTC, date, datetime, time, timedelta, tzinfo
from enum import StrEnum

from fermata.i18n import t


class PeriodKind(StrEnum):
    DAY = "day"
    WEEK = "week"


def first_day_of(kind: PeriodKind, anchor: date) -> date:
    """The day itself, or the Monday of its week."""
    if kind == PeriodKind.DAY:
        return anchor
    return anchor - timedelta(days=anchor.weekday())


def last_day_of(kind: PeriodKind, anchor: date) -> date:
    """The day itself, or the Sunday of its week."""
    if kind == PeriodKind.DAY:
        return anchor
    return first_day_of(kind, anchor) + timedelta(days=6)


def shift(kind: PeriodKind, anchor: date, steps: int) -> date:
    """The anchor `steps` periods later (earlier if negative)."""
    days_per_period = 1 if kind == PeriodKind.DAY else 7
    return anchor + timedelta(days=steps * days_per_period)


def utc_bounds(
    kind: PeriodKind, anchor: date, zone: tzinfo | None = None
) -> tuple[datetime, datetime]:
    """From the start of the period (included) to the start of the next one (excluded), in UTC.

    The days are those of `zone`; without one, of the time zone of this computer.
    """
    start = _midnight(first_day_of(kind, anchor), zone)
    end = _midnight(last_day_of(kind, anchor) + timedelta(days=1), zone)
    return start, end


def _midnight(day: date, zone: tzinfo | None) -> datetime:
    # Without a zone the datetime is naive, and `astimezone` reads it in the local time.
    return datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)


def period_title(kind: PeriodKind, anchor: date) -> str:
    """`Tue, 3 Nov 2026` for a day, `2 Nov – 8 Nov 2026` for a week."""
    first = first_day_of(kind, anchor)
    if kind == PeriodKind.DAY:
        return t(
            "history.day_title",
            weekday=weekday_name(first),
            day=first.day,
            month=month_name(first),
            year=first.year,
        )
    last = last_day_of(kind, anchor)
    values = {
        "first_day": first.day,
        "first_month": month_name(first),
        "last_day": last.day,
        "last_month": month_name(last),
    }
    if first.year == last.year:
        return t("history.week_title", year=first.year, **values)
    return t(
        "history.week_title_two_years",
        first_year=first.year,
        last_year=last.year,
        **values,
    )


def weekday_name(day: date | datetime) -> str:
    return t(f"history.weekday.{day.weekday()}")


def month_name(day: date | datetime) -> str:
    return t(f"history.month.{day.month}")

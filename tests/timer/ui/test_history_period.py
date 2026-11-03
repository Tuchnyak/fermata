import os
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from timer.ui.history_period import (
    PeriodKind,
    first_day_of,
    last_day_of,
    period_title,
    shift,
    utc_bounds,
)

DAY, WEEK = PeriodKind.DAY, PeriodKind.WEEK

# 2026-11-03 is a Tuesday: its week runs from Monday 2 Nov to Sunday 8 Nov.
TUESDAY = date(2026, 11, 3)
MONDAY = date(2026, 11, 2)
SUNDAY = date(2026, 11, 8)


# --- the days of a period ------------------------------------------------------


def test_a_day_starts_and_ends_on_the_day_itself():
    assert first_day_of(DAY, TUESDAY) == TUESDAY
    assert last_day_of(DAY, TUESDAY) == TUESDAY


@pytest.mark.parametrize("anchor", [MONDAY, TUESDAY, SUNDAY])
def test_a_week_runs_from_monday_to_sunday_whichever_day_is_the_anchor(anchor):
    assert first_day_of(WEEK, anchor) == MONDAY
    assert last_day_of(WEEK, anchor) == SUNDAY


def test_a_week_can_cross_a_month_and_a_year():
    assert first_day_of(WEEK, date(2026, 12, 31)) == date(2026, 12, 28)
    assert last_day_of(WEEK, date(2026, 12, 31)) == date(2027, 1, 3)


# --- moving between periods --------------------------------------------------


def test_the_next_and_the_previous_day():
    assert shift(DAY, TUESDAY, 1) == date(2026, 11, 4)
    assert shift(DAY, TUESDAY, -1) == date(2026, 11, 2)


def test_the_next_and_the_previous_week_move_the_anchor_by_seven_days():
    assert shift(WEEK, TUESDAY, 1) == date(2026, 11, 10)
    assert shift(WEEK, TUESDAY, -1) == date(2026, 10, 27)


def test_moving_crosses_a_month_and_a_year():
    assert shift(DAY, date(2026, 12, 31), 1) == date(2027, 1, 1)
    assert shift(WEEK, date(2026, 1, 3), -1) == date(2025, 12, 27)


# --- the bounds in UTC -----------------------------------------------------------


def utc(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=UTC)


def test_a_day_in_utc_runs_from_midnight_to_midnight():
    assert utc_bounds(DAY, TUESDAY, UTC) == (utc(2026, 11, 3), utc(2026, 11, 4))


def test_a_week_runs_to_the_midnight_after_its_sunday():
    assert utc_bounds(WEEK, TUESDAY, UTC) == (utc(2026, 11, 2), utc(2026, 11, 9))


def test_the_days_are_the_days_of_the_time_zone():
    moscow = timezone(timedelta(hours=3))

    assert utc_bounds(DAY, TUESDAY, moscow) == (utc(2026, 11, 2, 21), utc(2026, 11, 3, 21))


def test_a_day_when_the_clocks_change_is_one_hour_shorter():
    berlin = ZoneInfo("Europe/Berlin")  # the clocks go forward on 2026-03-29

    start, end = utc_bounds(DAY, date(2026, 3, 29), berlin)

    assert (start, end) == (utc(2026, 3, 28, 23), utc(2026, 3, 29, 22))
    assert end - start == timedelta(hours=23)


@contextmanager
def computer_time_zone(name):
    old = os.environ.get("TZ")
    os.environ["TZ"] = name
    time.tzset()
    try:
        yield
    finally:
        if old is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = old
        time.tzset()


def test_without_a_zone_the_days_are_those_of_this_computer():
    with computer_time_zone("Asia/Tokyo"):  # UTC+9, no summer time
        bounds = utc_bounds(DAY, TUESDAY)

    assert bounds == (utc(2026, 11, 2, 15), utc(2026, 11, 3, 15))


def test_the_bounds_are_aware_datetimes_in_utc():
    start, end = utc_bounds(DAY, TUESDAY, timezone(timedelta(hours=3)))

    assert start.utcoffset() == timedelta(0)
    assert end.utcoffset() == timedelta(0)


# --- the title -----------------------------------------------------------------


def test_the_title_of_a_day():
    assert period_title(DAY, TUESDAY) == "Tue, 3 Nov 2026"


def test_the_title_of_a_week_names_its_first_and_last_day():
    assert period_title(WEEK, TUESDAY) == "2 Nov – 8 Nov 2026"
    assert period_title(WEEK, date(2026, 10, 28)) == "26 Oct – 1 Nov 2026"


def test_the_title_of_a_week_across_a_new_year_names_both_years():
    assert period_title(WEEK, date(2026, 12, 31)) == "28 Dec 2026 – 3 Jan 2027"

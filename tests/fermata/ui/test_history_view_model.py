from datetime import UTC, datetime, timedelta, timezone

import pytest
from fermata.i18n import CATALOG, t
from fermata.intervals import IntervalKind, IntervalStatus, RunningInterval
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.history import HistoryRepository
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.sessions import SessionRepository
from fermata.ui.history_period import PeriodKind
from fermata.ui.history_view_model import (
    CategoryTotal,
    HistoryRow,
    HistoryViewModel,
)

MOSCOW = timezone(timedelta(hours=3))
# The fake clock says 2026-01-01 12:00 UTC: Thursday 1 January, 15:00 in Moscow.


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def session_repository(db):
    return SessionRepository(db)


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def work_id(category_repository):
    return category_repository.create("Work", "#112233").id


@pytest.fixture
def reading_id(category_repository):
    return category_repository.create("Reading", "#445566").id


@pytest.fixture
def history_view_model(db, clock):
    return HistoryViewModel(HistoryRepository(db), clock, MOSCOW)


def record(
    session_repository,
    started_at,
    category_id,
    *,
    status=IntervalStatus.COMPLETED,
    actual_seconds=25 * 60,
    kind=IntervalKind.WORK,
):
    session_id = session_repository.create_flow(started_at)
    interval_id = session_repository.start_interval(
        session_id,
        1,
        RunningInterval(kind, category_id, 25 * 60, started_at),
    )
    session_repository.finish_interval(
        interval_id,
        status=status,
        actual_seconds=actual_seconds,
        ended_at=started_at + timedelta(minutes=25),
    )


def utc(day, hour, minute=0, month=1, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# --- the period ------------------------------------------------------------------


def test_it_starts_on_today_in_the_local_time(history_view_model):
    view = history_view_model.view()

    assert view.kind == PeriodKind.DAY
    assert view.title == "Thu, 1 Jan 2026"


def test_today_is_the_day_of_the_clock_in_the_local_zone(db, clock):
    clock.advance(10 * 3600)  # 22:00 UTC, already 01:00 on the 2nd in Moscow
    view_model = HistoryViewModel(HistoryRepository(db), clock, MOSCOW)

    assert view_model.view().title == "Fri, 2 Jan 2026"


def test_previous_and_next_move_by_a_day(history_view_model):
    history_view_model.previous()
    assert history_view_model.view().title == "Wed, 31 Dec 2025"

    history_view_model.next()
    history_view_model.next()
    assert history_view_model.view().title == "Fri, 2 Jan 2026"


def test_a_week_runs_from_monday_to_sunday(history_view_model):
    history_view_model.show_week()

    view = history_view_model.view()

    assert view.kind == PeriodKind.WEEK
    assert view.title == "29 Dec 2025 – 4 Jan 2026"


def test_previous_and_next_move_by_a_week_in_the_week_view(history_view_model):
    history_view_model.show_week()

    history_view_model.previous()
    assert history_view_model.view().title == "22 Dec – 28 Dec 2025"

    history_view_model.next()
    history_view_model.next()
    assert history_view_model.view().title == "5 Jan – 11 Jan 2026"


def test_switching_between_day_and_week_keeps_the_day(history_view_model):
    history_view_model.previous()  # Wednesday 31 December
    history_view_model.show_week()
    history_view_model.show_day()

    assert history_view_model.view().title == "Wed, 31 Dec 2025"


def test_today_goes_back_to_the_current_day_or_week(history_view_model):
    history_view_model.previous()
    history_view_model.previous()
    history_view_model.go_to_today()
    assert history_view_model.view().title == "Thu, 1 Jan 2026"

    history_view_model.show_week()
    history_view_model.next()
    history_view_model.go_to_today()
    assert history_view_model.view().title == "29 Dec 2025 – 4 Jan 2026"


# --- the list -------------------------------------------------------------------


def test_a_day_with_no_work_is_empty(history_view_model):
    view = history_view_model.view()

    assert view.rows == []
    assert view.totals == []
    assert view.total == "0m"


def test_a_row_shows_the_color_the_category_the_local_time_the_duration_and_the_outcome(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(1, 9, 30), work_id)  # 12:30 in Moscow

    assert history_view_model.view().rows == [
        HistoryRow("#112233", "Work", "12:30", "25m", "Completed")
    ]


def test_the_rows_are_in_the_order_the_intervals_started(
    history_view_model, session_repository, work_id, reading_id
):
    record(session_repository, utc(1, 10), reading_id)
    record(session_repository, utc(1, 6), work_id)

    assert [row.started for row in history_view_model.view().rows] == ["09:00", "13:00"]


@pytest.mark.parametrize(
    ("status", "text"),
    [
        (IntervalStatus.COMPLETED, "Completed"),
        (IntervalStatus.SKIPPED, "Skipped"),
        (IntervalStatus.STOPPED, "Stopped"),
    ],
)
def test_the_outcome_is_named(history_view_model, session_repository, work_id, status, text):
    record(session_repository, utc(1, 9), work_id, status=status, actual_seconds=600)

    (row,) = history_view_model.view().rows
    assert (row.status, row.duration) == (text, "10m")


def test_an_interrupted_interval_has_a_dash_for_its_duration(
    history_view_model, session_repository, work_id
):
    record(
        session_repository, utc(1, 9), work_id,
        status=IntervalStatus.INTERRUPTED, actual_seconds=None,
    )

    (row,) = history_view_model.view().rows
    assert (row.status, row.duration) == ("Interrupted", "—")


def test_a_long_interval_is_shown_in_hours_and_minutes(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(1, 9), work_id, actual_seconds=65 * 60)

    assert history_view_model.view().rows[0].duration == "1h 05m"


def test_breaks_are_not_listed(history_view_model, session_repository, work_id):
    record(session_repository, utc(1, 9), None, kind=IntervalKind.SHORT_BREAK)

    assert history_view_model.view().rows == []


def test_only_the_intervals_of_the_period_are_listed(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(1, 9), work_id)
    record(session_repository, utc(2, 9), work_id)
    record(session_repository, utc(31, 9, month=12, year=2025), work_id)

    assert len(history_view_model.view().rows) == 1


def test_the_day_is_the_local_day_not_the_utc_one(
    history_view_model, session_repository, work_id
):
    record(session_repository, datetime(2025, 12, 31, 21, 30, tzinfo=UTC), work_id)  # 00:30 on 1 Jan in Moscow
    record(session_repository, datetime(2026, 1, 1, 21, 30, tzinfo=UTC), work_id)  # 00:30 on 2 Jan

    (row,) = history_view_model.view().rows
    assert row.started == "00:30"

    history_view_model.next()
    assert [row.started for row in history_view_model.view().rows] == ["00:30"]


def test_in_a_week_the_start_of_an_interval_has_its_weekday(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(1, 9, 30), work_id)  # Thursday
    record(session_repository, utc(29, 9, month=12, year=2025), work_id)  # Monday 29 December
    record(session_repository, utc(4, 9), work_id)  # Sunday 4 January
    record(session_repository, utc(5, 9), work_id)  # Monday 5 January: the next week
    history_view_model.show_week()

    assert [row.started for row in history_view_model.view().rows] == [
        "Mon 12:00",
        "Thu 12:30",
        "Sun 12:00",
    ]


# --- the totals -------------------------------------------------------------------


def test_the_totals_are_the_actual_time_per_category_longest_first(
    history_view_model, session_repository, work_id, reading_id
):
    record(session_repository, utc(1, 5), reading_id, actual_seconds=20 * 60)
    record(session_repository, utc(1, 6), work_id, actual_seconds=25 * 60)
    record(session_repository, utc(1, 7), reading_id, actual_seconds=15 * 60)

    view = history_view_model.view()

    assert view.totals == [
        CategoryTotal("#445566", "Reading", "35m"),
        CategoryTotal("#112233", "Work", "25m"),
    ]
    assert view.total == "1h 00m"


def test_skipped_and_stopped_intervals_count_for_the_time_they_ran(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(1, 5), work_id, status=IntervalStatus.SKIPPED, actual_seconds=10 * 60)
    record(session_repository, utc(1, 6), work_id, status=IntervalStatus.STOPPED, actual_seconds=5 * 60)

    assert history_view_model.view().total == "15m"


def test_an_interrupted_interval_does_not_count(
    history_view_model, session_repository, work_id, reading_id
):
    record(session_repository, utc(1, 5), work_id, actual_seconds=25 * 60)
    record(
        session_repository, utc(1, 6), reading_id,
        status=IntervalStatus.INTERRUPTED, actual_seconds=None,
    )

    view = history_view_model.view()

    assert view.totals == [CategoryTotal("#112233", "Work", "25m")]
    assert view.total == "25m"
    assert len(view.rows) == 2


def test_the_totals_of_a_week_add_up_its_days(
    history_view_model, session_repository, work_id
):
    record(session_repository, utc(29, 9, month=12, year=2025), work_id)
    record(session_repository, utc(1, 9), work_id)
    record(session_repository, utc(4, 9), work_id)
    history_view_model.show_week()

    view = history_view_model.view()

    assert view.totals == [CategoryTotal("#112233", "Work", "1h 15m")]
    assert view.total == "1h 15m"


def test_the_totals_follow_the_period(history_view_model, session_repository, work_id):
    record(session_repository, utc(1, 9), work_id)
    record(session_repository, utc(2, 9), work_id, actual_seconds=10 * 60)
    history_view_model.next()

    assert history_view_model.view().total == "10m"


# --- strings -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        *(f"history.weekday.{number}" for number in range(7)),
        *(f"history.month.{number}" for number in range(1, 13)),
        "history.day_title",
        "history.week_title",
        "history.week_title_two_years",
        "history.start_in_week",
        "history.no_duration",
        "history.day",
        "history.week",
        "history.today",
        "history.previous",
        "history.next",
        "history.empty",
        "history.total",
        "history.column.category",
        "history.column.started",
        "history.column.duration",
        "history.column.status",
        *(f"history.status.{status}" for status in IntervalStatus),
    ],
)
def test_the_texts_of_the_history_exist_in_the_catalog(key):
    assert key in CATALOG
    assert t(key, weekday="Mon", day=1, month="Jan", year=2026, time="12:00",
             first_day=1, first_month="Jan", last_day=2, last_month="Jan",
             first_year=2026, last_year=2027)

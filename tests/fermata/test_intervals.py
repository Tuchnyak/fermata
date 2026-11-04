import pytest
from fermata.intervals import IntervalKind, IntervalStatus, next_kind, planned_seconds
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.settings import Settings

WORK = IntervalKind.WORK
SHORT = IntervalKind.SHORT_BREAK
LONG = IntervalKind.LONG_BREAK

DEFAULT_SETTINGS = Settings()


# --- kinds and statuses in the database ---------------------------------------

STARTED = "2026-01-01T12:00:00Z"


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


def insert_interval(db, kind, status=None):
    """Insert an interval of the given kind and status; the table's checks must accept it."""
    session_id = db.insert(
        "INSERT INTO session (kind, status, started_at) VALUES ('flow', 'running', :started_at)",
        {"started_at": STARTED},
    )
    category_id = 1 if kind == WORK else None  # 1 is the system category `None`
    db.insert(
        "INSERT INTO interval (session_id, position, kind, category_id, planned_seconds,"
        " started_at, status)"
        " VALUES (:session_id, 1, :kind, :category_id, 1500, :started_at, :status)",
        {
            "session_id": session_id,
            "kind": kind,
            "category_id": category_id,
            "started_at": STARTED,
            "status": status,
        },
    )


def stored_column(db, column):
    return db.query_one(
        f"SELECT {column} FROM interval", mapper=lambda row: row[column]
    )


@pytest.mark.parametrize("kind", list(IntervalKind))
def test_the_interval_table_accepts_every_interval_kind(db, kind):
    insert_interval(db, kind)

    assert stored_column(db, "kind") == kind


@pytest.mark.parametrize("status", list(IntervalStatus))
def test_the_interval_table_accepts_every_interval_status(db, status):
    insert_interval(db, WORK, status)

    assert stored_column(db, "status") == status


# --- sequencing --------------------------------------------------------------


def test_a_session_starts_with_a_work_interval():
    assert next_kind([], DEFAULT_SETTINGS) == WORK


@pytest.mark.parametrize(
    ("finished", "expected"),
    [
        ([WORK], SHORT),
        ([WORK, SHORT], WORK),
        ([WORK, SHORT, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK], LONG),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG, WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK], LONG),
    ],
)  # fmt: skip
def test_with_default_settings_a_long_break_follows_every_fourth_work_interval(
    finished, expected
):
    assert next_kind(finished, DEFAULT_SETTINGS) == expected


@pytest.mark.parametrize(
    ("long_break_every", "finished", "expected"),
    [
        (1, [WORK], LONG),
        (1, [WORK, LONG], WORK),
        (1, [WORK, LONG, WORK], LONG),
        (2, [WORK], SHORT),
        (2, [WORK, SHORT, WORK], LONG),
        (2, [WORK, SHORT, WORK, LONG, WORK], SHORT),
        (2, [WORK, SHORT, WORK, LONG, WORK, SHORT, WORK], LONG),
        (3, [WORK, SHORT, WORK], SHORT),
        (3, [WORK, SHORT, WORK, SHORT, WORK], LONG),
    ],
)
def test_long_break_comes_after_every_nth_work_interval(
    long_break_every, finished, expected
):
    settings = Settings(long_break_every=long_break_every)

    assert next_kind(finished, settings) == expected


@pytest.mark.parametrize(
    "finished",
    [
        [WORK, SHORT],
        [WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG],
        [WORK, WORK, SHORT],
    ],
)
def test_a_work_interval_follows_any_break(finished):
    assert next_kind(finished, DEFAULT_SETTINGS) == WORK


def test_the_same_history_gives_a_different_break_for_a_different_n():
    finished = [WORK, SHORT, WORK]

    assert next_kind(finished, Settings(long_break_every=4)) == SHORT
    assert next_kind(finished, Settings(long_break_every=2)) == LONG


# --- lengths -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"), [(WORK, 25 * 60), (SHORT, 5 * 60), (LONG, 15 * 60)]
)
def test_default_lengths_are_taken_from_the_default_settings(kind, expected):
    assert planned_seconds(kind, DEFAULT_SETTINGS) == expected


@pytest.mark.parametrize(
    ("kind", "expected"), [(WORK, 30 * 60), (SHORT, 10 * 60), (LONG, 20 * 60)]
)
def test_lengths_are_taken_from_the_given_settings(kind, expected):
    settings = Settings(work_minutes=30, short_break_minutes=10, long_break_minutes=20)

    assert planned_seconds(kind, settings) == expected

import re
import sqlite3

import pytest
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate

STARTED = "2026-10-19T09:00:00Z"
ENDED = "2026-10-19T09:25:00Z"
SCENARIO = {"scenario_name": "Work day", "scenario_snapshot": "{}"}


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


def add_category(db: Db, name, color="#112233"):
    return db.insert(
        "INSERT INTO category (name, color) VALUES (:name, :color)",
        {"name": name, "color": color},
    )


def add_scenario(db: Db, name="Work day", repeat_count=1):
    return db.insert(
        "INSERT INTO scenario (name, repeat_count) VALUES (:name, :repeat_count)",
        {"name": name, "repeat_count": repeat_count},
    )


def add_scenario_row(db: Db, scenario_id, **overrides):
    values = {
        "scenario_id": scenario_id,
        "position": 1,
        "category_id": 1,  # the system category `None`
        "count": 2,
    } | overrides
    return db.insert(
        "INSERT INTO scenario_row (scenario_id, position, category_id, count)"
        " VALUES (:scenario_id, :position, :category_id, :count)",
        values,
    )


def add_session(db: Db, **overrides):
    values = {
        "kind": "flow",
        "status": "running",
        "started_at": STARTED,
        "scenario_name": None,
        "scenario_snapshot": None,
    } | overrides
    return db.insert(
        "INSERT INTO session (kind, status, started_at, scenario_name, scenario_snapshot)"
        " VALUES (:kind, :status, :started_at, :scenario_name, :scenario_snapshot)",
        values,
    )


def add_interval(db: Db, session_id, **overrides):
    values = {
        "session_id": session_id,
        "position": 1,
        "kind": "work",
        "category_id": 1,  # the system category `None`
        "planned_seconds": 1500,
        "actual_seconds": 1500,
        "started_at": STARTED,
        "ended_at": ENDED,
        "status": "completed",
    } | overrides
    return db.insert(
        "INSERT INTO interval (session_id, position, kind, category_id, planned_seconds,"
        " actual_seconds, started_at, ended_at, status)"
        " VALUES (:session_id, :position, :kind, :category_id, :planned_seconds,"
        " :actual_seconds, :started_at, :ended_at, :status)",
        values,
    )


def row_of(db: Db, table, id):
    return db.query_one(
        f"SELECT * FROM {table} WHERE id = ?", (id,), mapper=lambda row: dict(row)
    )


def names_in_sqlite_master(db: Db, type):
    return db.query(
        "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name",
        (type,),
        mapper=lambda row: row["name"],
    )


# --- migration ---------------------------------------------------------------


def test_migration_creates_all_tables_and_the_view_and_sets_version_1(db):
    version = db.query_one("PRAGMA user_version", mapper=lambda row: row[0])

    assert names_in_sqlite_master(db, "table") == [
        "category",
        "interval",
        "scenario",
        "scenario_row",
        "session",
        "setting",
    ]
    assert names_in_sqlite_master(db, "view") == ["interval_details"]
    assert version == 1


# --- category ----------------------------------------------------------------


def test_system_category_none_exists_after_migration(db):
    categories = db.query("SELECT * FROM category", mapper=lambda row: dict(row))

    assert len(categories) == 1
    assert categories[0]["id"] == 1
    assert categories[0]["name"] == "None"
    assert categories[0]["is_system"] == 1
    assert categories[0]["is_archived"] == 0
    assert re.fullmatch(r"#[0-9a-f]{6}", categories[0]["color"])


def test_new_category_is_neither_system_nor_archived(db):
    category = row_of(db, "category", add_category(db, "Work"))

    assert category["name"] == "Work"
    assert category["color"] == "#112233"
    assert category["is_system"] == 0
    assert category["is_archived"] == 0


def test_category_name_is_unique_ignoring_case(db):
    add_category(db, "Work")

    with pytest.raises(sqlite3.IntegrityError):
        add_category(db, "WORK")


def test_name_of_the_system_category_is_reserved(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_category(db, "none")


# --- scenario ----------------------------------------------------------------


def test_new_scenario_has_no_timer_overrides(db):
    scenario = row_of(db, "scenario", add_scenario(db, repeat_count=2))

    assert scenario["name"] == "Work day"
    assert scenario["repeat_count"] == 2
    assert scenario["work_minutes"] is None
    assert scenario["short_break_minutes"] is None
    assert scenario["long_break_minutes"] is None
    assert scenario["long_break_every"] is None


def test_scenario_name_is_unique_ignoring_case(db):
    add_scenario(db, "Work day")

    with pytest.raises(sqlite3.IntegrityError):
        add_scenario(db, "WORK DAY")


def test_scenario_repeats_at_least_once(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_scenario(db, repeat_count=0)


def test_scenario_row_count_is_at_least_one(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_scenario_row(db, add_scenario(db), count=0)


def test_scenario_row_must_reference_an_existing_scenario(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_scenario_row(db, scenario_id=999)


def test_scenario_row_must_reference_an_existing_category(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_scenario_row(db, add_scenario(db), category_id=999)


def test_row_position_is_unique_within_a_scenario_but_not_across_scenarios(db):
    first = add_scenario(db, "First")
    add_scenario_row(db, first, position=1)

    with pytest.raises(sqlite3.IntegrityError):
        add_scenario_row(db, first, position=1)

    add_scenario_row(db, add_scenario(db, "Second"), position=1)


def test_deleting_a_scenario_deletes_its_rows(db):
    scenario_id = add_scenario(db)
    add_scenario_row(db, scenario_id, position=1)
    add_scenario_row(db, scenario_id, position=2)

    db.execute("DELETE FROM scenario WHERE id = ?", (scenario_id,))

    rows = db.query("SELECT id FROM scenario_row", mapper=lambda row: row["id"])
    assert rows == []


# --- session -----------------------------------------------------------------


@pytest.mark.parametrize("kind", ["flow", "scenario"])
@pytest.mark.parametrize("status", ["running", "completed", "stopped", "interrupted"])
def test_session_accepts_allowed_kinds_and_statuses(db, kind, status):
    scenario = SCENARIO if kind == "scenario" else {}

    session = row_of(db, "session", add_session(db, kind=kind, status=status, **scenario))

    assert (session["kind"], session["status"]) == (kind, status)
    assert session["ended_at"] is None


@pytest.mark.parametrize(
    "overrides",
    [{"kind": "other"}, {"status": "done"}, {"status": "paused"}],
)
def test_session_rejects_other_kinds_and_statuses(db, overrides):
    with pytest.raises(sqlite3.IntegrityError):
        add_session(db, **overrides)


def test_session_requires_a_start_time(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_session(db, started_at=None)


@pytest.mark.parametrize("missing", ["scenario_name", "scenario_snapshot"])
def test_scenario_session_requires_a_name_and_a_snapshot(db, missing):
    with pytest.raises(sqlite3.IntegrityError):
        add_session(db, kind="scenario", **(SCENARIO | {missing: None}))


@pytest.mark.parametrize("extra", ["scenario_name", "scenario_snapshot"])
def test_flow_session_has_no_name_and_no_snapshot(db, extra):
    with pytest.raises(sqlite3.IntegrityError):
        add_session(db, kind="flow", **{extra: SCENARIO[extra]})


def test_deleting_a_scenario_keeps_its_sessions(db):
    scenario_id = add_scenario(db, "Work day")
    session_id = add_session(db, kind="scenario", **SCENARIO)

    db.execute("DELETE FROM scenario WHERE id = ?", (scenario_id,))

    session = row_of(db, "session", session_id)
    assert session["scenario_name"] == "Work day"
    assert session["scenario_snapshot"] == "{}"


# --- interval ----------------------------------------------------------------


@pytest.mark.parametrize("status", ["completed", "skipped", "stopped", "interrupted"])
def test_interval_accepts_allowed_statuses(db, status):
    interval_id = add_interval(db, add_session(db), status=status)

    assert row_of(db, "interval", interval_id)["status"] == status


@pytest.mark.parametrize("kind", ["short_break", "long_break"])
def test_break_has_no_category(db, kind):
    interval_id = add_interval(db, add_session(db), kind=kind, category_id=None)

    interval = row_of(db, "interval", interval_id)

    assert interval["kind"] == kind
    assert interval["category_id"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "other"},
        {"kind": "session"},
        {"status": "running"},
        {"status": "done"},
        {"kind": "short_break"},  # a break must not have a category
        {"category_id": None},  # a work interval must have one
    ],
)
def test_interval_rejects_invalid_values(db, overrides):
    with pytest.raises(sqlite3.IntegrityError):
        add_interval(db, add_session(db), **overrides)


def test_interrupted_interval_has_no_actual_duration(db):
    interval_id = add_interval(
        db, add_session(db), status="interrupted", actual_seconds=None, ended_at=None
    )

    assert row_of(db, "interval", interval_id)["actual_seconds"] is None


def test_unfinished_interval_has_no_status_end_or_actual_duration(db):
    interval_id = add_interval(
        db, add_session(db), status=None, actual_seconds=None, ended_at=None
    )

    interval = row_of(db, "interval", interval_id)

    assert (interval["status"], interval["ended_at"], interval["actual_seconds"]) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize("column", ["started_at", "planned_seconds"])
def test_interval_requires_start_time_and_planned_duration(db, column):
    with pytest.raises(sqlite3.IntegrityError):
        add_interval(db, add_session(db), **{column: None})


def test_interval_must_reference_an_existing_session(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_interval(db, session_id=999)


def test_interval_must_reference_an_existing_category(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_interval(db, add_session(db), category_id=999)


def test_position_is_unique_within_a_session_but_not_across_sessions(db):
    first = add_session(db)
    add_interval(db, first, position=1)

    with pytest.raises(sqlite3.IntegrityError):
        add_interval(db, first, position=1)

    add_interval(db, add_session(db), position=1)


# --- setting -----------------------------------------------------------------


def test_setting_key_is_unique(db):
    db.execute("INSERT INTO setting (key, value) VALUES ('a', '1')")

    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO setting (key, value) VALUES ('a', '2')")


# --- interval_details view ---------------------------------------------------


def test_interval_details_adds_category_and_session_data(db):
    reading = add_category(db, "Reading", "#aabbcc")
    flow = add_session(db)
    scenario = add_session(db, kind="scenario", **SCENARIO)
    add_interval(db, flow, position=1, category_id=reading)
    add_interval(db, flow, position=2, kind="short_break", category_id=None)
    add_interval(db, scenario, position=1, category_id=reading)

    rows = db.query(
        """
        SELECT session_id, position, kind, category_name, category_color,
               session_kind, scenario_name
        FROM interval_details
        ORDER BY session_id, position
        """,
        mapper=lambda row: tuple(row),
    )

    assert rows == [
        (flow, 1, "work", "Reading", "#aabbcc", "flow", None),
        (flow, 2, "short_break", None, None, "flow", None),
        (scenario, 1, "work", "Reading", "#aabbcc", "scenario", "Work day"),
    ]


def test_interval_details_keeps_all_interval_columns(db):
    interval_id = add_interval(db, add_session(db))

    details = db.query_one(
        "SELECT * FROM interval_details WHERE id = ?",
        (interval_id,),
        mapper=lambda row: dict(row),
    )

    assert details.items() >= row_of(db, "interval", interval_id).items()


# --- analysis ----------------------------------------------------------------


def test_worked_time_per_category_per_week_can_be_queried(db):
    work = add_category(db, "Work")
    reading = add_category(db, "Reading")
    session_id = add_session(db)
    # Week of Monday 2026-10-19: Monday and Sunday work intervals; the break is not counted.
    add_interval(
        db, session_id, position=1, category_id=work,
        started_at="2026-10-19T09:00:00Z", actual_seconds=1500,
    )
    add_interval(
        db, session_id, position=2, category_id=work,
        started_at="2026-10-25T20:00:00Z", actual_seconds=600,
    )
    add_interval(
        db, session_id, position=3, kind="short_break", category_id=None,
        started_at="2026-10-25T20:10:00Z", actual_seconds=300,
    )
    # Week of Monday 2026-10-26; the interrupted interval has no actual duration.
    add_interval(
        db, session_id, position=4, category_id=reading,
        started_at="2026-10-26T09:00:00Z", actual_seconds=900,
    )
    add_interval(
        db, session_id, position=5, category_id=reading, status="interrupted",
        started_at="2026-10-26T10:00:00Z", actual_seconds=None,
    )

    rows = db.query(
        """
        SELECT date(started_at, 'weekday 0', '-6 days') AS week_start,
               category_name,
               SUM(actual_seconds) AS seconds
        FROM interval_details
        WHERE kind = 'work'
        GROUP BY week_start, category_name
        ORDER BY week_start, category_name
        """,
        mapper=lambda row: (row["week_start"], row["category_name"], row["seconds"]),
    )

    assert rows == [
        ("2026-10-19", "Work", 2100),
        ("2026-10-26", "Reading", 900),
    ]

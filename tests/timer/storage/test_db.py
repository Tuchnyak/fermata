import sqlite3

import pytest
from timer.storage.db import Db


@pytest.fixture
def db():
    db = Db.open(":memory:")
    db.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    db.execute(
        "CREATE TABLE child ("
        "id INTEGER PRIMARY KEY, "
        "parent_id INTEGER NOT NULL REFERENCES parent(id))"
    )
    return db


def name_of(row):
    return row["name"]


def test_open_accepts_a_file_path(tmp_path):
    path = tmp_path / "test.db"
    db = Db.open(path)

    db.execute("CREATE TABLE t (x INTEGER)")
    db.insert("INSERT INTO t (x) VALUES (1)")

    assert path.exists()
    assert db.query("SELECT x FROM t", mapper=lambda row: row["x"]) == [1]


def test_rows_are_readable_by_column_name(db):
    db.insert("INSERT INTO parent (name) VALUES ('a')")

    row = db.query_one(
        "SELECT id, name FROM parent", mapper=lambda row: (row["id"], row["name"])
    )

    assert row == (1, "a")


def test_insert_returns_the_new_id(db):
    first = db.insert("INSERT INTO parent (name) VALUES ('a')")
    second = db.insert("INSERT INTO parent (name) VALUES ('b')")

    assert (first, second) == (1, 2)


def test_execute_returns_the_number_of_affected_rows(db):
    db.insert("INSERT INTO parent (name) VALUES ('a')")
    db.insert("INSERT INTO parent (name) VALUES ('b')")

    assert db.execute("UPDATE parent SET name = 'x'") == 2
    assert db.execute("DELETE FROM parent WHERE name = 'nobody'") == 0


def test_query_returns_mapped_objects_in_order(db):
    for name in ("a", "b", "c"):
        db.insert("INSERT INTO parent (name) VALUES (?)", (name,))

    assert db.query("SELECT name FROM parent ORDER BY id", mapper=name_of) == ["a", "b", "c"]


def test_query_returns_empty_list_when_nothing_matches(db):
    assert db.query("SELECT name FROM parent", mapper=name_of) == []


def test_query_one_returns_the_mapped_object(db):
    db.insert("INSERT INTO parent (name) VALUES ('a')")

    assert db.query_one("SELECT name FROM parent WHERE id = 1", mapper=name_of) == "a"


def test_query_one_returns_the_first_row_when_several_match(db):
    db.insert("INSERT INTO parent (name) VALUES ('a')")
    db.insert("INSERT INTO parent (name) VALUES ('b')")

    assert db.query_one("SELECT name FROM parent ORDER BY id", mapper=name_of) == "a"


def test_query_one_returns_none_when_nothing_matches(db):
    assert db.query_one("SELECT name FROM parent WHERE id = 1", mapper=name_of) is None


def test_positional_parameters(db):
    db.insert("INSERT INTO parent (name) VALUES (?)", ("a",))

    found = db.query("SELECT name FROM parent WHERE name = ?", ("a",), mapper=name_of)

    assert found == ["a"]


def test_named_parameters(db):
    db.insert("INSERT INTO parent (name) VALUES (:name)", {"name": "a"})

    found = db.query(
        "SELECT name FROM parent WHERE name = :name", {"name": "a"}, mapper=name_of
    )

    assert found == ["a"]


def test_foreign_key_violation_raises(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.insert("INSERT INTO child (parent_id) VALUES (99)")

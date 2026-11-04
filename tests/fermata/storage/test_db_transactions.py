import pytest
from fermata.storage.db import Db


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    Db.open(path).execute("CREATE TABLE item (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    return path


@pytest.fixture
def db(db_path):
    return Db.open(db_path)


@pytest.fixture
def other(db_path):
    """A second connection to the same file: sees only what `db` has committed."""
    return Db.open(db_path)


def names(db):
    return db.query("SELECT name FROM item ORDER BY id", mapper=lambda row: row["name"])


def test_statement_outside_a_transaction_is_committed_immediately(db, other):
    db.insert("INSERT INTO item (name) VALUES ('a')")

    assert names(other) == ["a"]


def test_transaction_commits_when_the_block_ends(db, other):
    with db.transaction():
        db.insert("INSERT INTO item (name) VALUES ('a')")
        db.insert("INSERT INTO item (name) VALUES ('b')")

    assert names(other) == ["a", "b"]


def test_changes_are_not_committed_before_the_block_ends(db, other):
    with db.transaction():
        db.insert("INSERT INTO item (name) VALUES ('a')")

        assert names(db) == ["a"]
        assert names(other) == []


def test_exception_rolls_everything_back_and_is_reraised(db, other):
    with pytest.raises(ValueError):
        with db.transaction():
            db.insert("INSERT INTO item (name) VALUES ('a')")
            db.insert("INSERT INTO item (name) VALUES ('b')")
            raise ValueError("boom")

    assert names(db) == []
    assert names(other) == []


def test_nested_transaction_raises_an_error(db):
    with db.transaction():
        with pytest.raises(RuntimeError):
            with db.transaction():
                pass


def test_outer_transaction_survives_a_rejected_nested_one(db, other):
    with db.transaction():
        db.insert("INSERT INTO item (name) VALUES ('a')")
        with pytest.raises(RuntimeError):
            with db.transaction():
                pass

    assert names(other) == ["a"]


def test_new_transaction_can_start_after_a_failed_one(db, other):
    with pytest.raises(ValueError):
        with db.transaction():
            raise ValueError("boom")

    with db.transaction():
        db.insert("INSERT INTO item (name) VALUES ('a')")

    assert names(other) == ["a"]

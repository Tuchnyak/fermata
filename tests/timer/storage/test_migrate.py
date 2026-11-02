import sqlite3

import pytest
from timer.storage.db import Db
from timer.storage.migrate import migrate


@pytest.fixture
def db():
    return Db.open(":memory:")


@pytest.fixture
def migrations(tmp_path):
    directory = tmp_path / "migrations"
    directory.mkdir()
    return directory


def add(migrations, name, sql):
    (migrations / name).write_text(sql)


def version(db: Db):
    return db.query_one("PRAGMA user_version", mapper=lambda row: row[0])


def tables(db: Db):
    return db.query(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name",
        mapper=lambda row: row["name"],
    )


def values(db: Db):
    return db.query("SELECT x FROM a ORDER BY x", mapper=lambda row: row["x"])


def test_fresh_database_gets_all_migrations_in_order(db, migrations):
    add(migrations, "002_fill_a.sql", "INSERT INTO a (x) VALUES (1);")
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")

    migrate(db, migrations)

    assert version(db) == 2
    assert values(db) == [1]


def test_second_run_changes_nothing(db, migrations):
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")
    add(migrations, "002_fill_a.sql", "INSERT INTO a (x) VALUES (1);")

    migrate(db, migrations)
    migrate(db, migrations)

    assert version(db) == 2
    assert values(db) == [1]


def test_older_database_gets_only_the_missing_migrations(db, migrations):
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")
    migrate(db, migrations)
    add(migrations, "002_fill_a.sql", "INSERT INTO a (x) VALUES (1);")

    migrate(db, migrations)

    assert version(db) == 2
    assert values(db) == [1]


def test_migration_file_may_contain_several_statements(db, migrations):
    add(
        migrations,
        "001_create_a.sql",
        "CREATE TABLE a (x INTEGER);\n"
        "INSERT INTO a (x) VALUES (1);\n"
        "INSERT INTO a (x) VALUES (2);\n",
    )

    migrate(db, migrations)

    assert values(db) == [1, 2]


def test_files_not_matching_the_pattern_are_ignored(db, migrations):
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")
    add(migrations, "README.md", "not sql")
    add(migrations, "draft.sql", "THIS IS NOT SQL;")

    migrate(db, migrations)

    assert version(db) == 1


def test_database_newer_than_the_migrations_is_rejected_without_changes(db, migrations):
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")
    db.execute("PRAGMA user_version = 5")

    with pytest.raises(RuntimeError):
        migrate(db, migrations)

    assert version(db) == 5
    assert tables(db) == []


def test_failing_migration_is_rolled_back_and_version_is_not_advanced(db, migrations):
    add(migrations, "001_create_a.sql", "CREATE TABLE a (x INTEGER);")
    add(
        migrations,
        "002_broken.sql",
        "CREATE TABLE b (x INTEGER);\nINSERT INTO missing VALUES (1);",
    )

    with pytest.raises(sqlite3.OperationalError):
        migrate(db, migrations)

    assert version(db) == 1
    assert tables(db) == ["a"]

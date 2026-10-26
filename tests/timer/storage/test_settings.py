from dataclasses import replace

import pytest
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.settings import Settings, SettingsRepository

DEFAULT_SETTINGS = Settings(
    work_minutes=25,
    short_break_minutes=5,
    long_break_minutes=15,
    long_break_every=4,
    transition_mode="confirm",
    blink=True,
)


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def settings_repository(db):
    return SettingsRepository(db)


def stored_settings(db: Db):
    return db.query(
        "SELECT key, value FROM setting ORDER BY key",
        mapper=lambda row: (row["key"], row["value"]),
    )


def test_defaults_apply_when_nothing_is_stored(settings_repository):
    assert settings_repository.get_all() == DEFAULT_SETTINGS


def test_defaults_are_not_written_to_the_database(db, settings_repository):
    settings_repository.get_all()

    assert stored_settings(db) == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("work_minutes", 30),
        ("short_break_minutes", 10),
        ("long_break_minutes", 20),
        ("long_break_every", 3),
        ("transition_mode", "auto"),
        ("transition_mode", "mixed"),
        ("blink", False),
    ],
)
def test_a_stored_value_is_returned_with_its_type(settings_repository, key, value):
    settings_repository.set(key, value)

    result = getattr(settings_repository.get_all(), key)

    assert result == value
    assert type(result) is type(value)


def test_setting_one_value_leaves_the_others_at_their_defaults(settings_repository):
    settings_repository.set("work_minutes", 50)

    assert settings_repository.get_all() == replace(DEFAULT_SETTINGS, work_minutes=50)


def test_setting_a_value_again_replaces_it(db, settings_repository):
    settings_repository.set("work_minutes", 30)
    settings_repository.set("work_minutes", 40)

    assert settings_repository.get_all().work_minutes == 40
    assert stored_settings(db) == [("work_minutes", "40")]


def test_all_values_can_be_stored_together(settings_repository):
    settings_repository.set("work_minutes", 30)
    settings_repository.set("short_break_minutes", 10)
    settings_repository.set("long_break_minutes", 20)
    settings_repository.set("long_break_every", 3)
    settings_repository.set("transition_mode", "mixed")
    settings_repository.set("blink", False)

    assert settings_repository.get_all() == Settings(
        work_minutes=30,
        short_break_minutes=10,
        long_break_minutes=20,
        long_break_every=3,
        transition_mode="mixed",
        blink=False,
    )


def test_values_survive_reopening_the_database(tmp_path):
    path = tmp_path / "test.db"
    first = Db.open(path)
    migrate(first, MIGRATIONS_DIR)
    SettingsRepository(first).set("work_minutes", 30)
    SettingsRepository(first).set("blink", False)

    reopened = SettingsRepository(Db.open(path)).get_all()

    assert reopened.work_minutes == 30
    assert reopened.blink is False


def test_values_are_stored_as_plain_text_for_own_queries(db, settings_repository):
    settings_repository.set("work_minutes", 30)
    settings_repository.set("transition_mode", "mixed")
    settings_repository.set("blink", False)

    assert stored_settings(db) == [
        ("blink", "0"),
        ("transition_mode", "mixed"),
        ("work_minutes", "30"),
    ]

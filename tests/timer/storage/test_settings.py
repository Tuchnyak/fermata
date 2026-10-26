from dataclasses import replace

import pytest
from timer.i18n import t
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.settings import Settings, SettingsRepository
from timer.validation import ValidationError

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


# --- store and read ----------------------------------------------------------


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


# --- validation --------------------------------------------------------------

MINUTE_KEYS = ["work_minutes", "short_break_minutes", "long_break_minutes"]


@pytest.mark.parametrize("key", MINUTE_KEYS)
@pytest.mark.parametrize("value", [1, 60, 180])
def test_minutes_from_1_to_180_are_accepted(settings_repository, key, value):
    settings_repository.set(key, value)

    assert getattr(settings_repository.get_all(), key) == value


@pytest.mark.parametrize("key", MINUTE_KEYS)
@pytest.mark.parametrize("value", [0, -1, 181, 1000])
def test_minutes_out_of_range_are_rejected(settings_repository, key, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set(key, value)

    assert error.value.key == "setting.minutes_invalid"


@pytest.mark.parametrize("value", [1, 4, 20])
def test_long_break_every_from_1_to_20_is_accepted(settings_repository, value):
    settings_repository.set("long_break_every", value)

    assert settings_repository.get_all().long_break_every == value


@pytest.mark.parametrize("value", [0, -1, 21, 100])
def test_long_break_every_out_of_range_is_rejected(settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("long_break_every", value)

    assert error.value.key == "setting.long_break_every_invalid"


@pytest.mark.parametrize("value", ["auto", "confirm", "mixed"])
def test_known_transition_modes_are_accepted(settings_repository, value):
    settings_repository.set("transition_mode", value)

    assert settings_repository.get_all().transition_mode == value


@pytest.mark.parametrize("value", ["", "manual", "AUTO", " auto", 1, None])
def test_unknown_transition_mode_is_rejected(settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("transition_mode", value)

    assert error.value.key == "setting.transition_mode_invalid"


@pytest.mark.parametrize("value", [True, False])
def test_blink_accepts_a_boolean(settings_repository, value):
    settings_repository.set("blink", value)

    assert settings_repository.get_all().blink is value


@pytest.mark.parametrize("value", [1, 0, "1", "true", None])
def test_blink_rejects_anything_but_a_boolean(settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("blink", value)

    assert error.value.key == "setting.blink_invalid"


@pytest.mark.parametrize("key", [*MINUTE_KEYS, "long_break_every"])
@pytest.mark.parametrize("value", ["25", 25.0, True, None])
def test_a_number_setting_rejects_a_value_that_is_not_an_integer(
    settings_repository, key, value
):
    with pytest.raises(ValidationError):
        settings_repository.set(key, value)


@pytest.mark.parametrize("key", ["", "theme", "Work_Minutes", "work minutes"])
def test_unknown_key_is_rejected(settings_repository, key):
    with pytest.raises(ValidationError) as error:
        settings_repository.set(key, 25)

    assert error.value.key == "setting.unknown_key"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("work_minutes", 0),
        ("long_break_every", 21),
        ("transition_mode", "manual"),
        ("blink", "yes"),
        ("theme", "dark"),
    ],
)
def test_rejected_value_is_not_stored(db, settings_repository, key, value):
    with pytest.raises(ValidationError):
        settings_repository.set(key, value)

    assert stored_settings(db) == []


def test_rejected_value_keeps_the_previous_one(settings_repository):
    settings_repository.set("work_minutes", 30)

    with pytest.raises(ValidationError):
        settings_repository.set("work_minutes", 500)

    assert settings_repository.get_all().work_minutes == 30


@pytest.mark.parametrize(
    "key",
    [
        "setting.unknown_key",
        "setting.minutes_invalid",
        "setting.long_break_every_invalid",
        "setting.transition_mode_invalid",
        "setting.blink_invalid",
    ],
)
def test_error_messages_exist_in_the_catalog(key):
    assert t(key)

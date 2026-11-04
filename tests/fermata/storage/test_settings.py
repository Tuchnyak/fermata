from dataclasses import replace

import pytest
from fermata.i18n import t
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.settings import Settings, SettingsRepository
from fermata.storage.settings_rules import (
    LONG_BREAK_EVERY_RANGE,
    LONG_BREAK_MINUTES_RANGE,
    SHORT_BREAK_MINUTES_RANGE,
    THEME_IDS,
    TRANSITION_MODES,
    WORK_MINUTES_RANGE,
)
from fermata.validation import ValidationError

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


def test_sound_is_on_by_default(settings_repository):
    assert settings_repository.get_all().sound is True


def test_sound_can_be_turned_off_and_on(settings_repository):
    settings_repository.set("sound", False)

    assert settings_repository.get_all().sound is False

    settings_repository.set("sound", True)

    assert settings_repository.get_all().sound is True


@pytest.mark.parametrize("value", ["yes", 1, 0, None])
def test_sound_must_be_a_boolean(db, settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("sound", value)

    assert error.value.key == "setting.sound_invalid"


def test_the_theme_is_dark_by_default(settings_repository):
    assert settings_repository.get_all().theme == "dark"


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_every_theme_can_be_stored(settings_repository, theme_id):
    settings_repository.set("theme", theme_id)

    assert settings_repository.get_all().theme == theme_id


@pytest.mark.parametrize("value", ["", "Dark", "nonsense", 1, None])
def test_the_theme_must_be_one_of_the_themes(settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("theme", value)

    assert error.value.key == "setting.theme_invalid"


def test_no_window_geometry_is_stored_by_default(settings_repository):
    assert settings_repository.get_all().window_geometry == ""


def test_a_window_geometry_can_be_stored_and_replaced(db, settings_repository):
    settings_repository.set("window_geometry", "900x700+100+50")
    settings_repository.set("window_geometry", "800x600+0+0")

    assert settings_repository.get_all().window_geometry == "800x600+0+0"
    assert stored_settings(db) == [("window_geometry", "800x600+0+0")]


@pytest.mark.parametrize("value", ["", "nonsense", "720x680", "0x680+0+0", 5, None])
def test_the_window_geometry_must_be_a_readable_one(db, settings_repository, value):
    with pytest.raises(ValidationError) as error:
        settings_repository.set("window_geometry", value)

    assert error.value.key == "setting.window_geometry_invalid"
    assert stored_settings(db) == []


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

MINUTE_LIMITS = [
    ("work_minutes", 1, 120),
    ("short_break_minutes", 1, 30),
    ("long_break_minutes", 1, 60),
]
MINUTE_KEYS = ["work_minutes", "short_break_minutes", "long_break_minutes"]


@pytest.mark.parametrize(("key", "lowest", "highest"), MINUTE_LIMITS)
def test_minutes_within_the_limits_of_the_setting_are_accepted(
    settings_repository, key, lowest, highest
):
    for value in (lowest, (lowest + highest) // 2, highest):
        settings_repository.set(key, value)

        assert getattr(settings_repository.get_all(), key) == value


@pytest.mark.parametrize(("key", "lowest", "highest"), MINUTE_LIMITS)
def test_minutes_outside_the_limits_of_the_setting_are_rejected(
    settings_repository, key, lowest, highest
):
    for value in (lowest - 1, -1, highest + 1, highest * 10):
        with pytest.raises(ValidationError) as error:
            settings_repository.set(key, value)

        assert error.value.key == f"setting.{key}_invalid"


@pytest.mark.parametrize("value", [1, 4, 10])
def test_long_break_every_from_1_to_20_is_accepted(settings_repository, value):
    settings_repository.set("long_break_every", value)

    assert settings_repository.get_all().long_break_every == value


@pytest.mark.parametrize("value", [0, -1, 11, 100])
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


@pytest.mark.parametrize("key", ["", "volume", "Work_Minutes", "work minutes"])
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
        ("volume", "dark"),
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
        "setting.work_minutes_invalid",
        "setting.short_break_minutes_invalid",
        "setting.long_break_minutes_invalid",
        "setting.long_break_every_invalid",
        "setting.transition_mode_invalid",
        "setting.blink_invalid",
        "setting.window_geometry_invalid",
    ],
)
def test_error_messages_exist_in_the_catalog(key):
    assert t(key)


# --- set_many ----------------------------------------------------------------


def test_set_many_stores_all_the_values(settings_repository):
    settings_repository.set_many(
        {"work_minutes": 30, "long_break_every": 3, "transition_mode": "auto", "blink": False}
    )

    assert settings_repository.get_all() == replace(
        DEFAULT_SETTINGS,
        work_minutes=30,
        long_break_every=3,
        transition_mode="auto",
        blink=False,
    )


def test_set_many_stores_nothing_when_one_value_is_invalid(db, settings_repository):
    with pytest.raises(ValidationError) as error:
        settings_repository.set_many(
            {"work_minutes": 30, "short_break_minutes": 0, "blink": False}
        )

    assert error.value.key == "setting.short_break_minutes_invalid"
    assert stored_settings(db) == []


def test_set_many_keeps_the_previous_values_when_one_value_is_invalid(settings_repository):
    settings_repository.set("work_minutes", 40)

    with pytest.raises(ValidationError):
        settings_repository.set_many({"work_minutes": 30, "long_break_every": 99})

    assert settings_repository.get_all().work_minutes == 40


def test_set_many_rejects_an_unknown_key_and_stores_nothing(db, settings_repository):
    with pytest.raises(ValidationError) as error:
        settings_repository.set_many({"work_minutes": 30, "volume": "dark"})

    assert error.value.key == "setting.unknown_key"
    assert stored_settings(db) == []


def test_set_many_with_no_changes_does_nothing(db, settings_repository):
    settings_repository.set_many({})

    assert stored_settings(db) == []


# --- limits shown to the user ------------------------------------------------


@pytest.mark.parametrize(
    ("key", "limits", "expected"),
    [
        ("work_minutes", WORK_MINUTES_RANGE, (1, 120)),
        ("short_break_minutes", SHORT_BREAK_MINUTES_RANGE, (1, 30)),
        ("long_break_minutes", LONG_BREAK_MINUTES_RANGE, (1, 60)),
        ("long_break_every", LONG_BREAK_EVERY_RANGE, (1, 10)),
    ],
)
def test_the_limits_are_those_the_rules_enforce(
    settings_repository, key, limits, expected
):
    assert limits == expected
    lowest, highest = limits
    settings_repository.set(key, lowest)
    settings_repository.set(key, highest)
    for outside in (lowest - 1, highest + 1):
        with pytest.raises(ValidationError):
            settings_repository.set(key, outside)


def test_the_transition_modes_are_the_ones_the_rules_accept(settings_repository):
    assert TRANSITION_MODES == ("auto", "confirm", "mixed")
    for mode in TRANSITION_MODES:
        settings_repository.set("transition_mode", mode)

import pytest
from timer.i18n import t
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.storage.settings import Settings, SettingsRepository
from timer.storage.settings_rules import TRANSITION_MODES
from timer.ui.settings_view_model import SettingsViewModel


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def settings_repository(db):
    return SettingsRepository(db)


@pytest.fixture
def settings_view_model(settings_repository):
    return SettingsViewModel(settings_repository)


def form_values(**changes):
    """What the form holds: the defaults, as text for the numbers, with some changes."""
    values = {
        "work_minutes": "25",
        "short_break_minutes": "5",
        "long_break_minutes": "15",
        "long_break_every": "4",
        "transition_mode": "confirm",
        "blink": True,
        "sound": True,
    }
    return values | changes


def stored_rows(db):
    return db.query(
        "SELECT key, value FROM setting ORDER BY key",
        mapper=lambda row: (row["key"], row["value"]),
    )


# --- showing and saving ------------------------------------------------------


def test_the_form_starts_with_the_default_settings(settings_view_model):
    assert settings_view_model.settings() == Settings()


def test_saved_values_become_the_settings(settings_view_model):
    message = settings_view_model.save(
        **form_values(
            work_minutes="30",
            short_break_minutes="10",
            long_break_minutes="20",
            long_break_every="3",
            transition_mode="mixed",
            blink=False,
        )
    )

    assert message is None
    assert settings_view_model.settings() == Settings(
        work_minutes=30,
        short_break_minutes=10,
        long_break_minutes=20,
        long_break_every=3,
        transition_mode="mixed",
        blink=False,
    )


def test_spaces_around_a_number_are_ignored(settings_view_model):
    message = settings_view_model.save(**form_values(work_minutes="  30 "))

    assert message is None
    assert settings_view_model.settings().work_minutes == 30


def test_saving_the_defaults_stores_nothing(db, settings_view_model):
    settings_view_model.save(**form_values())

    assert stored_rows(db) == []


def test_only_the_changed_values_are_stored(db, settings_view_model):
    settings_view_model.save(**form_values(work_minutes="30", blink=False))

    assert stored_rows(db) == [("blink", "0"), ("work_minutes", "30")]


# --- rejected input ----------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "text", "key"),
    [
        ("work_minutes", "0", "setting.work_minutes_invalid"),
        ("work_minutes", "121", "setting.work_minutes_invalid"),
        ("work_minutes", "-5", "setting.work_minutes_invalid"),
        ("work_minutes", "abc", "setting.work_minutes_invalid"),
        ("work_minutes", "", "setting.work_minutes_invalid"),
        ("work_minutes", "2.5", "setting.work_minutes_invalid"),
        ("short_break_minutes", "0", "setting.short_break_minutes_invalid"),
        ("short_break_minutes", "31", "setting.short_break_minutes_invalid"),
        ("long_break_minutes", "x", "setting.long_break_minutes_invalid"),
        ("long_break_minutes", "61", "setting.long_break_minutes_invalid"),
        ("long_break_every", "0", "setting.long_break_every_invalid"),
        ("long_break_every", "11", "setting.long_break_every_invalid"),
        ("long_break_every", "abc", "setting.long_break_every_invalid"),
        ("transition_mode", "manual", "setting.transition_mode_invalid"),
    ],
)
def test_invalid_input_gives_the_message_and_stores_nothing(
    db, settings_view_model, field, text, key
):
    message = settings_view_model.save(**form_values(**{field: text}))

    assert message == t(key)
    assert stored_rows(db) == []


def test_one_invalid_value_stops_the_valid_ones_from_being_saved(
    db, settings_view_model
):
    message = settings_view_model.save(
        **form_values(work_minutes="30", long_break_every="99")
    )

    assert message == t("setting.long_break_every_invalid")
    assert stored_rows(db) == []
    assert settings_view_model.settings().work_minutes == 25


# --- strings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "settings.work_minutes",
        "settings.short_break_minutes",
        "settings.long_break_minutes",
        "settings.long_break_every",
        "settings.transition_mode",
        "settings.blink",
        "settings.save",
        "settings.saved",
    ],
)
def test_the_labels_of_the_form_exist_in_the_catalog(key):
    assert t(key)


@pytest.mark.parametrize("mode", TRANSITION_MODES)
def test_every_transition_mode_has_a_name_and_an_explanation(mode):
    assert t(f"settings.mode.{mode}.name")
    assert t(f"settings.mode.{mode}.description")


def test_sound_is_saved_with_the_other_settings(db, settings_view_model):
    message = settings_view_model.save(**form_values(sound=False))

    assert message is None
    assert settings_view_model.settings().sound is False
    assert stored_rows(db) == [("sound", "0")]


# --- the theme ---------------------------------------------------------------------


def test_the_themes_are_offered_with_their_names(settings_view_model):
    assert settings_view_model.themes() == [
        ("light", "Light"),
        ("dark", "Dark"),
        ("catppuccin_latte", "Catppuccin Latte"),
        ("catppuccin_frappe", "Catppuccin Frappé"),
        ("catppuccin_macchiato", "Catppuccin Macchiato"),
        ("catppuccin_mocha", "Catppuccin Mocha"),
    ]


def test_a_chosen_theme_is_stored_at_once(db, settings_view_model):
    message = settings_view_model.choose_theme("catppuccin_mocha")

    assert message is None
    assert settings_view_model.settings().theme == "catppuccin_mocha"
    assert stored_rows(db) == [("theme", "catppuccin_mocha")]


def test_an_unknown_theme_is_refused_and_nothing_is_stored(db, settings_view_model):
    message = settings_view_model.choose_theme("nonsense")

    assert message == t("setting.theme_invalid")
    assert stored_rows(db) == []


def test_saving_the_other_settings_leaves_the_theme_alone(settings_view_model):
    settings_view_model.choose_theme("light")

    settings_view_model.save(**form_values(work_minutes="30"))

    assert settings_view_model.settings().theme == "light"
    assert settings_view_model.settings().work_minutes == 30

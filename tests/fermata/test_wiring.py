import pytest
from fermata import i18n
from fermata.background_sound import BackgroundSound
from fermata.intervals import IntervalKind
from fermata.sound import SoundEvent
from fermata.storage.db import Db
from fermata.wiring import build_components


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "fermata.db"


class RecordingPlayer:
    def __init__(self):
        self.played = []

    def play(self, sound):
        self.played.append(sound)


@pytest.fixture
def player():
    return RecordingPlayer()


@pytest.fixture
def components(database_path, clock, player):
    return build_components(database_path, clock, player)


def stored_sessions(database_path):
    return Db.open(database_path).query(
        "SELECT * FROM session ORDER BY id", mapper=dict
    )


def stored_intervals(database_path):
    return Db.open(database_path).query(
        "SELECT * FROM interval ORDER BY session_id, position", mapper=dict
    )


def start_flow(components):
    category = components.categories_view_model.categories()[0]
    components.home_view_model.select(category.id)
    components.home_view_model.start()


def test_creates_the_database_with_its_schema(database_path, components):
    assert database_path.exists()
    categories = components.categories_view_model.categories()
    assert [category.name for category in categories] == ["None"]


def test_starting_a_flow_writes_a_running_session_and_interval(
    database_path, components
):
    start_flow(components)

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["running"]
    assert [(i["kind"], i["status"]) for i in intervals] == [("work", None)]


def test_stopping_the_flow_closes_its_rows(database_path, clock, components):
    start_flow(components)
    clock.advance(60)

    components.engine.stop()

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["stopped"]
    assert [(i["status"], i["actual_seconds"]) for i in intervals] == [("stopped", 60)]


def test_the_category_of_the_previous_flow_is_preselected_after_stop(components):
    components.categories_view_model.add("Study", "#112233")
    category = next(
        category
        for category in components.categories_view_model.categories()
        if category.name == "Study"
    )
    components.home_view_model.select(category.id)
    components.home_view_model.start()
    components.engine.stop()

    components.home_view_model.preselect()

    assert components.home_view_model.selected_category().id == category.id


def test_settings_saved_in_the_ui_apply_to_the_next_flow(components):
    message = components.settings_view_model.save(
        work_minutes="30",
        short_break_minutes="5",
        long_break_minutes="15",
        long_break_every="4",
        transition_mode="confirm",
        blink=True,
        sound=True,
    )
    assert message is None

    start_flow(components)

    interval = components.engine.current_interval
    assert interval.kind == IntervalKind.WORK
    assert interval.planned_seconds == 30 * 60


def test_an_interval_left_running_is_interrupted_by_the_next_start(
    database_path, clock, components
):
    start_flow(components)
    clock.advance(60)
    # The window is closed here: nothing stops the flow.

    restarted = build_components(database_path, clock)

    sessions = stored_sessions(database_path)
    intervals = stored_intervals(database_path)
    assert [session["status"] for session in sessions] == ["interrupted"]
    assert [(i["status"], i["actual_seconds"]) for i in intervals] == [
        ("interrupted", None)
    ]
    assert restarted.engine.current_interval is None


def test_a_scenario_started_from_the_ui_is_written_as_a_scenario_session(
    database_path, components
):
    components.categories_view_model.add("Study", "#112233")
    editor = components.scenarios_view_model.new_editor()
    editor.set_name("Day")
    assert editor.save() is None

    components.scenarios_view_model.start(editor.saved_scenario_id)

    (session,) = stored_sessions(database_path)
    assert (session["kind"], session["status"], session["scenario_name"]) == (
        "scenario",
        "running",
        "Day",
    )


def test_the_end_of_a_work_interval_plays_its_sound(components, clock, player):
    start_flow(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == [SoundEvent.WORK_END]


def test_the_end_of_a_break_plays_its_sound(components, clock, player):
    start_flow(components)
    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()
    components.engine.confirm()  # the break starts
    player.played.clear()

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == [SoundEvent.BREAK_END]


def test_skipping_and_stopping_are_silent(components, player):
    start_flow(components)

    components.engine.skip()
    components.engine.stop()

    assert player.played == []


def test_the_switch_in_the_settings_silences_the_sounds(components, clock, player):
    components.settings_view_model.save(
        work_minutes="25",
        short_break_minutes="5",
        long_break_minutes="15",
        long_break_every="4",
        transition_mode="confirm",
        blink=True,
        sound=False,
    )
    start_flow(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == []


def test_a_sound_is_still_recorded_with_the_history(components, clock, database_path, player):
    start_flow(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert [row["status"] for row in stored_intervals(database_path)] == ["completed"]


# --- the history ---------------------------------------------------------------


def test_a_finished_interval_shows_in_the_history_of_its_day(clock, components):
    start_flow(components)
    clock.advance(10 * 60)
    components.engine.stop()

    view = components.history_view_model.view()

    assert [(row.category, row.duration, row.status) for row in view.rows] == [
        ("None", "10m", "Stopped")
    ]
    assert view.total == "10m"


def test_the_running_interval_is_not_in_the_history_yet(clock, components):
    start_flow(components)
    clock.advance(10 * 60)

    assert components.history_view_model.view().rows == []


# --- the sound of the end of a scenario ----------------------------------------


def start_a_scenario_of_one_work_interval(components):
    editor = components.scenarios_view_model.new_editor()
    editor.set_name("Short")
    assert editor.save() is None
    components.scenarios_view_model.start(editor.saved_scenario_id)


def test_the_background_sound_follows_the_timer_and_the_settings(
    database_path, clock, player, tmp_path, monkeypatch
):
    (tmp_path / "rain.wav").write_bytes(b"sound")
    started = []

    def launch(command, **keywords):
        started.append(command)
        return type("Process", (), {"terminate": lambda self: None, "wait": lambda self, timeout: 0})()

    monkeypatch.setattr("fermata.wiring.SOUNDS_DIR", tmp_path)
    monkeypatch.setattr(
        "fermata.wiring.BackgroundSound",
        lambda engine, get_settings, sounds_dir: BackgroundSound(
            engine, get_settings, sounds_dir, which=lambda name: f"/usr/bin/{name}", launch=launch
        ),
    )
    components = build_components(database_path, clock, player)
    components.settings_view_model.choose_background_sound("rain")

    start_flow(components)
    components.background_sound.update()

    assert len(started) == 1
    assert started[0][-1] == str(tmp_path / "rain.wav")


def test_a_scenario_run_to_its_end_plays_the_sound_of_its_end(components, clock, player):
    start_a_scenario_of_one_work_interval(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == [SoundEvent.SCENARIO_END]


def test_skipping_the_last_interval_of_a_scenario_is_silent(components, player):
    start_a_scenario_of_one_work_interval(components)

    components.engine.skip()

    assert player.played == []


def test_the_mute_button_silences_the_end_of_an_interval(components, clock, player):
    components.settings_view_model.toggle_sound()
    start_flow(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == []


def test_pressing_the_mute_button_again_brings_the_sounds_back(components, clock, player):
    components.settings_view_model.toggle_sound()
    components.settings_view_model.toggle_sound()
    start_flow(components)

    clock.advance(components.engine.remaining_seconds())
    components.engine.tick()

    assert player.played == [SoundEvent.WORK_END]


# --- the language --------------------------------------------------------------------


def test_the_stored_language_is_the_one_the_application_starts_in(database_path, clock):
    first = build_components(database_path, clock)
    first.settings_view_model.choose_language("ru")
    i18n.set_language("en")

    build_components(database_path, clock)

    assert i18n.current_language() == "ru"


def test_the_application_starts_in_english_without_a_stored_language(components):
    assert i18n.current_language() == "en"

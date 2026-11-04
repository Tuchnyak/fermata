import pytest
from fermata.background_sound import BackgroundSound
from fermata.engine import Engine
from fermata.storage.settings import Settings

CATEGORY_ID = 1


class Holder:
    """The settings of the moment, changed by a test."""

    def __init__(self, **values):
        self.settings = Settings(**values)

    def change(self, **values):
        self.settings = Settings(**{**self.settings.__dict__, **values})

    def __call__(self):
        return self.settings


@pytest.fixture
def settings():
    return Holder(background_sound="rain")


@pytest.fixture
def engine(clock, settings):
    return Engine(get_settings=settings, clock=clock)


@pytest.fixture
def sounds_dir(tmp_path):
    (tmp_path / "rain.wav").write_bytes(b"sound")
    (tmp_path / "ticking.ogg").write_bytes(b"sound")
    (tmp_path / "white_noise.mp3").write_bytes(b"sound")
    return tmp_path


@pytest.fixture
def background(engine, settings, sounds_dir, output):
    return BackgroundSound(engine, settings, sounds_dir, output)


def run_to_the_end_of_the_interval(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


# --- when it plays -----------------------------------------------------------------


def test_nothing_plays_while_the_timer_is_idle(background, output):
    background.update()

    assert output.plays == []


def test_a_running_work_interval_plays_the_chosen_sound_in_a_loop(
    background, engine, output, sounds_dir
):
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert output.plays == [(sounds_dir / "rain.wav", True)]


def test_the_sound_is_started_once_however_often_it_is_asked(background, engine, output):
    engine.start_flow(CATEGORY_ID)

    background.update()
    background.update()
    background.update()

    assert len(output.plays) == 1


@pytest.mark.parametrize(
    ("sound", "file"),
    [("ticking", "ticking.ogg"), ("white_noise", "white_noise.mp3"), ("rain", "rain.wav")],
)
def test_each_sound_has_its_own_file(
    background, engine, settings, output, sounds_dir, sound, file
):
    settings.change(background_sound=sound)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert output.files == [sounds_dir / file]


# --- when it is silent -------------------------------------------------------------


def test_off_is_silent(background, engine, settings, output):
    settings.change(background_sound="off")
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert output.plays == []


def test_the_switch_of_the_sound_silences_it(background, engine, settings, output):
    settings.change(sound=False)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert output.plays == []


def test_a_pause_stops_it_and_resuming_starts_it_again(background, engine, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    engine.pause()
    background.update()
    assert output.running == []

    engine.resume()
    background.update()
    assert len(output.playbacks) == 2
    assert len(output.running) == 1


def test_the_end_of_the_interval_stops_it(background, engine, clock, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    run_to_the_end_of_the_interval(engine, clock)
    background.update()

    assert output.running == []


def test_a_break_is_silent(background, engine, clock, output):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the break starts
    background.update()

    assert output.running == []


def test_the_next_work_interval_plays_it_again(background, engine, clock, output):
    engine.start_flow(CATEGORY_ID)
    background.update()
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the break
    background.update()
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the next work interval
    background.update()

    assert len(output.playbacks) == 2
    assert len(output.running) == 1


def test_waiting_for_confirmation_is_silent(background, engine, clock, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    run_to_the_end_of_the_interval(engine, clock)  # waits: the mode is "confirm"
    background.update()

    assert engine.current_interval is None
    assert output.running == []


@pytest.mark.parametrize("ending", ["skip", "stop"])
def test_skipping_and_stopping_stop_it(background, engine, output, ending):
    engine.start_flow(CATEGORY_ID)
    background.update()

    getattr(engine, ending)()
    background.update()

    assert output.running == []


# --- a change of the settings applies at once ---------------------------------------


def test_another_choice_replaces_the_sound(background, engine, settings, output, sounds_dir):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="ticking")
    background.update()

    assert output.playbacks[0].stopped is True
    assert output.plays[1] == (sounds_dir / "ticking.ogg", True)
    assert len(output.running) == 1


def test_choosing_off_stops_it(background, engine, settings, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="off")
    background.update()

    assert output.running == []


def test_switching_the_sound_off_stops_it(background, engine, settings, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(sound=False)
    background.update()

    assert output.running == []


def test_choosing_a_sound_while_a_work_interval_runs_starts_it(
    background, engine, settings, output
):
    settings.change(background_sound="off")
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="rain")
    background.update()

    assert len(output.running) == 1


# --- what can go wrong is no more than silence ---------------------------------------


def test_a_missing_file_means_no_sound(engine, settings, tmp_path, output):
    background = BackgroundSound(engine, settings, tmp_path, output)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert output.plays == []


def test_no_sound_system_means_no_sound_and_no_error(
    engine, settings, sounds_dir, silent_output
):
    background = BackgroundSound(engine, settings, sounds_dir, silent_output)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert engine.current_interval is not None


def test_a_failed_start_is_not_tried_again_at_every_tick(
    engine, settings, sounds_dir, silent_output
):
    background = BackgroundSound(engine, settings, sounds_dir, silent_output)
    engine.start_flow(CATEGORY_ID)

    background.update()
    background.update()

    assert len(silent_output.plays) == 1


# --- closing the window --------------------------------------------------------------


def test_stopping_it_ends_the_sound(background, engine, output):
    engine.start_flow(CATEGORY_ID)
    background.update()

    background.stop()

    assert output.running == []


def test_stopping_it_when_nothing_plays_does_nothing(background, output):
    background.stop()

    assert output.playbacks == []

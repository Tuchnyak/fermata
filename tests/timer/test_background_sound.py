import subprocess

import pytest
from timer.background_sound import BackgroundSound
from timer.engine import Engine
from timer.storage.settings import Settings

CATEGORY_ID = 1


class FakeProcess:
    def __init__(self, command):
        self.command = command
        self.ended = False

    def terminate(self):
        self.ended = True

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0 if self.ended else None


class Launcher:
    """Stands in for `subprocess.Popen`: remembers what it was asked to start."""

    def __init__(self):
        self.processes = []
        self.keywords = []

    def __call__(self, command, **keywords):
        process = FakeProcess(command)
        self.processes.append(process)
        self.keywords.append(keywords)
        return process

    @property
    def commands(self):
        return [process.command for process in self.processes]

    @property
    def running(self):
        return [process for process in self.processes if not process.ended]


class Holder:
    """The settings of the moment, changed by a test."""

    def __init__(self, **values):
        self.settings = Settings(**values)

    def change(self, **values):
        self.settings = Settings(**{**self.settings.__dict__, **values})

    def __call__(self):
        return self.settings


def installed(*names):
    def which(name):
        return f"/usr/bin/{name}" if name in names else None

    return which


@pytest.fixture
def settings():
    return Holder(background_sound="rain")


@pytest.fixture
def engine(clock, settings):
    return Engine(get_settings=settings, clock=clock)


@pytest.fixture
def launcher():
    return Launcher()


@pytest.fixture
def sounds_dir(tmp_path):
    (tmp_path / "rain.wav").write_bytes(b"sound")
    (tmp_path / "ticking.ogg").write_bytes(b"sound")
    (tmp_path / "white_noise.mp3").write_bytes(b"sound")
    return tmp_path


@pytest.fixture
def background(engine, settings, sounds_dir, launcher):
    return BackgroundSound(
        engine, settings, sounds_dir, which=installed("ffplay", "timeout", "paplay"), launch=launcher
    )


def run_to_the_end_of_the_interval(engine, clock):
    clock.advance(engine.remaining_seconds())
    engine.tick()


# --- when it plays -----------------------------------------------------------------


def test_nothing_plays_while_the_timer_is_idle(background, launcher):
    background.update()

    assert launcher.commands == []


def test_a_running_work_interval_plays_the_chosen_sound_in_a_loop(
    background, engine, launcher, sounds_dir
):
    engine.start_flow(CATEGORY_ID)

    background.update()

    command = launcher.commands[0]
    assert command[2] == "/usr/bin/ffplay"
    assert command[-1] == str(sounds_dir / "rain.wav")
    assert ["-loop", "0"] == command[command.index("-loop") : command.index("-loop") + 2]
    assert "-nodisp" in command
    assert command[command.index("-loglevel") + 1] == "quiet"


def test_it_is_played_in_the_background_and_says_nothing(background, engine, launcher):
    engine.start_flow(CATEGORY_ID)

    background.update()

    keywords = launcher.keywords[0]
    assert keywords["stdout"] == subprocess.DEVNULL
    assert keywords["stderr"] == subprocess.DEVNULL


def test_the_player_is_started_once_however_often_it_is_asked(background, engine, launcher):
    engine.start_flow(CATEGORY_ID)

    background.update()
    background.update()
    background.update()

    assert len(launcher.processes) == 1


def test_the_player_is_ended_after_the_time_left_if_the_application_dies(
    background, engine, launcher
):
    engine.start_flow(CATEGORY_ID)

    background.update()

    command = launcher.commands[0]
    assert command[0] == "/usr/bin/timeout"
    seconds = float(command[1])
    assert engine.remaining_seconds() <= seconds <= engine.remaining_seconds() + 10


@pytest.mark.parametrize(
    ("sound", "file"),
    [("ticking", "ticking.ogg"), ("white_noise", "white_noise.mp3"), ("rain", "rain.wav")],
)
def test_each_sound_has_its_own_file(
    background, engine, settings, launcher, sounds_dir, sound, file
):
    settings.change(background_sound=sound)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands[0][-1] == str(sounds_dir / file)


# --- when it is silent -------------------------------------------------------------


def test_off_is_silent(background, engine, settings, launcher):
    settings.change(background_sound="off")
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands == []


def test_the_switch_of_the_sound_silences_it(background, engine, settings, launcher):
    settings.change(sound=False)
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands == []


def test_a_pause_stops_it_and_resuming_starts_it_again(background, engine, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    engine.pause()
    background.update()
    assert launcher.running == []

    engine.resume()
    background.update()
    assert len(launcher.processes) == 2
    assert len(launcher.running) == 1


def test_the_end_of_the_interval_stops_it(background, engine, clock, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    run_to_the_end_of_the_interval(engine, clock)
    background.update()

    assert launcher.running == []


def test_a_break_is_silent(background, engine, clock, launcher):
    engine.start_flow(CATEGORY_ID)
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the break starts
    background.update()

    assert launcher.running == []


def test_the_next_work_interval_plays_it_again(background, engine, clock, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the break
    background.update()
    run_to_the_end_of_the_interval(engine, clock)
    engine.confirm()  # the next work interval
    background.update()

    assert len(launcher.processes) == 2
    assert len(launcher.running) == 1


def test_waiting_for_confirmation_is_silent(background, engine, clock, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    run_to_the_end_of_the_interval(engine, clock)  # waits: the mode is "confirm"
    background.update()

    assert engine.current_interval is None
    assert launcher.running == []


@pytest.mark.parametrize("ending", ["skip", "stop"])
def test_skipping_and_stopping_stop_it(background, engine, launcher, ending):
    engine.start_flow(CATEGORY_ID)
    background.update()

    getattr(engine, ending)()
    background.update()

    assert launcher.running == []


# --- a change of the settings applies at once ---------------------------------------


def test_another_choice_replaces_the_sound(background, engine, settings, launcher, sounds_dir):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="ticking")
    background.update()

    assert launcher.processes[0].ended is True
    assert launcher.commands[1][-1] == str(sounds_dir / "ticking.ogg")
    assert len(launcher.running) == 1


def test_choosing_off_stops_it(background, engine, settings, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="off")
    background.update()

    assert launcher.running == []


def test_switching_the_sound_off_stops_it(background, engine, settings, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(sound=False)
    background.update()

    assert launcher.running == []


def test_choosing_a_sound_while_a_work_interval_runs_starts_it(
    background, engine, settings, launcher
):
    settings.change(background_sound="off")
    engine.start_flow(CATEGORY_ID)
    background.update()

    settings.change(background_sound="rain")
    background.update()

    assert len(launcher.running) == 1


# --- what can go wrong is no more than silence ---------------------------------------


def test_a_missing_file_means_no_sound(engine, settings, tmp_path, launcher):
    background = BackgroundSound(
        engine, settings, tmp_path, which=installed("ffplay", "timeout"), launch=launcher
    )
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands == []


def test_without_ffplay_there_is_no_sound(engine, settings, sounds_dir, launcher):
    background = BackgroundSound(
        engine, settings, sounds_dir, which=installed("paplay", "pw-play"), launch=launcher
    )
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands == []


def test_without_timeout_there_is_no_sound(engine, settings, sounds_dir, launcher):
    background = BackgroundSound(
        engine, settings, sounds_dir, which=installed("ffplay"), launch=launcher
    )
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert launcher.commands == []


def test_a_player_that_cannot_be_started_does_not_disturb_the_timer(
    engine, settings, sounds_dir
):
    def failing(command, **keywords):
        raise OSError("no such program")

    background = BackgroundSound(
        engine, settings, sounds_dir, which=installed("ffplay", "timeout"), launch=failing
    )
    engine.start_flow(CATEGORY_ID)

    background.update()

    assert engine.current_interval is not None


def test_a_failed_start_is_not_tried_again_at_every_tick(engine, settings, sounds_dir):
    attempts = []

    def failing(command, **keywords):
        attempts.append(command)
        raise OSError("no such program")

    background = BackgroundSound(
        engine, settings, sounds_dir, which=installed("ffplay", "timeout"), launch=failing
    )
    engine.start_flow(CATEGORY_ID)

    background.update()
    background.update()

    assert len(attempts) == 1


# --- closing the window --------------------------------------------------------------


def test_stopping_it_ends_the_player(background, engine, launcher):
    engine.start_flow(CATEGORY_ID)
    background.update()

    background.stop()

    assert launcher.running == []


def test_stopping_it_when_nothing_plays_does_nothing(background, launcher):
    background.stop()

    assert launcher.processes == []

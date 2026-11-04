import subprocess
from pathlib import Path

import pytest
from timer.engine import FlowEvent
from timer.intervals import FinishedInterval, IntervalKind, IntervalStatus, RunningInterval
from timer.sound import SoundEvent, SoundNotifier, SoundPlayer, sound_event_for
from timer.storage.settings import Settings


def finished(kind, status=IntervalStatus.COMPLETED, clock=None):
    return FinishedInterval(
        kind=kind,
        category_id=1 if kind == IntervalKind.WORK else None,
        planned_seconds=60,
        started_at=clock() if clock else None,
        ended_at=clock() if clock else None,
        actual_seconds=60,
        status=status,
    )


def event(clock, **fields):
    return FlowEvent(at=clock(), **fields)


# --- which sound an event calls for ----------------------------------------------


def test_a_completed_work_interval_calls_for_the_work_sound(clock):
    interval = finished(IntervalKind.WORK, clock=clock)

    assert sound_event_for(event(clock, finished_interval=interval)) == SoundEvent.WORK_END


@pytest.mark.parametrize("kind", [IntervalKind.SHORT_BREAK, IntervalKind.LONG_BREAK])
def test_a_completed_break_calls_for_the_break_sound(clock, kind):
    interval = finished(kind, clock=clock)

    assert sound_event_for(event(clock, finished_interval=interval)) == SoundEvent.BREAK_END


@pytest.mark.parametrize("status", [IntervalStatus.SKIPPED, IntervalStatus.STOPPED])
@pytest.mark.parametrize("kind", list(IntervalKind))
def test_an_interval_ended_by_the_user_is_silent(clock, kind, status):
    interval = finished(kind, status, clock)

    assert sound_event_for(event(clock, finished_interval=interval)) is None


def test_the_end_of_a_scenario_calls_for_its_own_sound(clock):
    interval = finished(IntervalKind.WORK, clock=clock)

    scenario_end = event(
        clock, finished_interval=interval, flow_ended=True, session_completed=True
    )

    assert sound_event_for(scenario_end) == SoundEvent.SCENARIO_END


def test_a_scenario_ended_by_skipping_its_last_interval_is_silent(clock):
    interval = finished(IntervalKind.WORK, IntervalStatus.SKIPPED, clock)

    scenario_end = event(
        clock, finished_interval=interval, flow_ended=True, session_completed=True
    )

    assert sound_event_for(scenario_end) is None


def test_a_work_interval_in_the_middle_of_a_scenario_calls_for_the_work_sound(clock):
    interval = finished(IntervalKind.WORK, clock=clock)

    assert sound_event_for(event(clock, finished_interval=interval)) == SoundEvent.WORK_END


def test_a_start_is_silent(clock):
    started = RunningInterval(IntervalKind.WORK, 1, 60, clock())

    assert sound_event_for(event(clock, flow_started=True, started_interval=started)) is None


def test_a_completed_interval_that_starts_the_next_one_calls_for_one_sound(clock):
    interval = finished(IntervalKind.WORK, clock=clock)
    started = RunningInterval(IntervalKind.SHORT_BREAK, None, 60, clock())

    both = event(clock, finished_interval=interval, started_interval=started)

    assert sound_event_for(both) == SoundEvent.WORK_END


# --- playing ---------------------------------------------------------------------


class FakeProcess:
    def __init__(self, command):
        self.command = command
        self.polls = 0
        self.finished = False

    def poll(self):
        self.polls += 1
        return 0 if self.finished else None


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


def installed(*names):
    """A `which` that knows only the given programs."""

    def which(name):
        return f"/usr/bin/{name}" if name in names else None

    return which


@pytest.fixture
def sounds_dir(tmp_path):
    return tmp_path


@pytest.fixture
def launcher():
    return Launcher()


def make_player(sounds_dir, launcher, *programs):
    return SoundPlayer(sounds_dir, which=installed(*programs), launch=launcher)


def put(sounds_dir, name):
    (sounds_dir / name).write_bytes(b"sound")
    return sounds_dir / name


def test_the_file_of_the_event_is_played_by_the_first_player_that_is_installed(
    sounds_dir, launcher
):
    path = put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, launcher, "pw-play", "aplay").play(SoundEvent.WORK_END)

    assert launcher.commands == [["/usr/bin/pw-play", str(path)]]


def test_each_event_has_its_own_file(sounds_dir, launcher):
    put(sounds_dir, "work_end.wav")
    path = put(sounds_dir, "break_end.wav")

    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.BREAK_END)

    assert launcher.commands == [["/usr/bin/paplay", str(path)]]


def test_the_end_of_a_scenario_has_its_own_file(sounds_dir, launcher):
    put(sounds_dir, "work_end.wav")
    path = put(sounds_dir, "scenario_end.wav")

    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.SCENARIO_END)

    assert launcher.commands == [["/usr/bin/paplay", str(path)]]


def test_without_its_own_file_the_end_of_a_scenario_plays_the_work_sound(
    sounds_dir, launcher
):
    path = put(sounds_dir, "work_end.wav")
    put(sounds_dir, "break_end.wav")

    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.SCENARIO_END)

    assert launcher.commands == [["/usr/bin/paplay", str(path)]]


def test_the_work_sound_does_not_fall_back_to_the_scenario_sound(sounds_dir, launcher):
    put(sounds_dir, "scenario_end.wav")

    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_the_end_of_a_scenario_is_silent_without_any_of_the_files(sounds_dir, launcher):
    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.SCENARIO_END)

    assert launcher.commands == []


@pytest.mark.parametrize("extension", ["wav", "ogg", "flac"])
def test_paplay_plays_what_it_knows(sounds_dir, launcher, extension):
    path = put(sounds_dir, f"work_end.{extension}")

    make_player(sounds_dir, launcher, "paplay", "ffplay").play(SoundEvent.WORK_END)

    assert launcher.commands == [["/usr/bin/paplay", str(path)]]


def test_an_mp3_is_played_by_ffplay_quietly_and_without_a_window(sounds_dir, launcher):
    path = put(sounds_dir, "work_end.mp3")

    make_player(sounds_dir, launcher, "paplay", "pw-play", "aplay", "ffplay").play(
        SoundEvent.WORK_END
    )

    assert launcher.commands == [
        ["/usr/bin/ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
    ]


def test_an_mp3_is_not_played_when_only_players_that_do_not_know_it_are_installed(
    sounds_dir, launcher
):
    put(sounds_dir, "work_end.mp3")

    make_player(sounds_dir, launcher, "paplay", "aplay").play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_aplay_plays_only_wav(sounds_dir, launcher):
    put(sounds_dir, "work_end.ogg")

    make_player(sounds_dir, launcher, "aplay").play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_a_wav_is_preferred_to_other_formats(sounds_dir, launcher):
    put(sounds_dir, "work_end.mp3")
    wav = put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, launcher, "ffplay").play(SoundEvent.WORK_END)

    assert launcher.commands[0][-1] == str(wav)


def test_a_missing_file_means_no_sound(sounds_dir, launcher):
    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_a_missing_directory_means_no_sound(tmp_path, launcher):
    player = make_player(tmp_path / "nowhere", launcher, "paplay")

    player.play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_no_player_installed_means_no_sound(sounds_dir, launcher):
    put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, launcher).play(SoundEvent.WORK_END)

    assert launcher.commands == []


def test_a_player_that_cannot_be_started_does_not_disturb_the_timer(sounds_dir):
    put(sounds_dir, "work_end.wav")

    def broken(command, **keywords):
        raise OSError("no such device")

    SoundPlayer(sounds_dir, which=installed("paplay"), launch=broken).play(SoundEvent.WORK_END)


def test_the_player_runs_in_the_background_and_says_nothing(sounds_dir, launcher):
    put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, launcher, "paplay").play(SoundEvent.WORK_END)

    (keywords,) = launcher.keywords
    assert keywords["stdout"] == subprocess.DEVNULL
    assert keywords["stderr"] == subprocess.DEVNULL
    assert keywords["start_new_session"] is True


def test_finished_players_are_collected(sounds_dir, launcher):
    put(sounds_dir, "work_end.wav")
    player = make_player(sounds_dir, launcher, "paplay")

    player.play(SoundEvent.WORK_END)
    launcher.processes[0].finished = True
    player.play(SoundEvent.WORK_END)

    assert launcher.processes[0].polls >= 1


def test_the_sounds_of_the_application_are_in_its_package():
    import timer.sound

    assert (Path(timer.sound.__file__).parent / "sounds").is_dir()


# --- the notifier ----------------------------------------------------------------


class RecordingPlayer:
    def __init__(self):
        self.played = []

    def play(self, sound):
        self.played.append(sound)


@pytest.fixture
def player():
    return RecordingPlayer()


def test_the_notifier_plays_what_an_event_calls_for(clock, player):
    notifier = SoundNotifier(Settings, player)

    notifier(event(clock, finished_interval=finished(IntervalKind.WORK, clock=clock)))

    assert player.played == [SoundEvent.WORK_END]


def test_the_notifier_plays_the_sound_of_the_end_of_a_scenario(clock, player):
    notifier = SoundNotifier(Settings, player)

    notifier(
        event(
            clock,
            finished_interval=finished(IntervalKind.WORK, clock=clock),
            flow_ended=True,
            session_completed=True,
        )
    )

    assert player.played == [SoundEvent.SCENARIO_END]


def test_the_notifier_stays_silent_for_an_event_without_a_sound(clock, player):
    notifier = SoundNotifier(Settings, player)

    notifier(event(clock, flow_started=True))

    assert player.played == []


def test_the_notifier_stays_silent_when_sound_is_off(clock, player):
    notifier = SoundNotifier(lambda: Settings(sound=False), player)

    notifier(event(clock, finished_interval=finished(IntervalKind.WORK, clock=clock)))

    assert player.played == []


def test_the_switch_is_read_each_time_a_sound_is_due(clock, player):
    settings = [Settings(sound=False)]
    notifier = SoundNotifier(lambda: settings[0], player)
    work_end = event(clock, finished_interval=finished(IntervalKind.WORK, clock=clock))

    notifier(work_end)
    settings[0] = Settings(sound=True)
    notifier(work_end)

    assert player.played == [SoundEvent.WORK_END]

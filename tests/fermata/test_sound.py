from pathlib import Path

import pytest
from fermata.engine import FlowEvent
from fermata.intervals import FinishedInterval, IntervalKind, IntervalStatus, RunningInterval
from fermata.sound import SoundEvent, SoundNotifier, SoundPlayer, sound_event_for
from fermata.storage.settings import Settings


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


@pytest.fixture
def sounds_dir(tmp_path):
    return tmp_path


def make_player(sounds_dir, output):
    return SoundPlayer(sounds_dir, output)


def put(sounds_dir, name):
    (sounds_dir / name).write_bytes(b"sound")
    return sounds_dir / name


def test_the_file_of_the_event_is_played(sounds_dir, output):
    path = put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.plays == [(path, False)]


def test_each_event_has_its_own_file(sounds_dir, output):
    put(sounds_dir, "work_end.wav")
    path = put(sounds_dir, "break_end.wav")

    make_player(sounds_dir, output).play(SoundEvent.BREAK_END)

    assert output.files == [path]


def test_the_end_of_a_scenario_has_its_own_file(sounds_dir, output):
    put(sounds_dir, "work_end.wav")
    path = put(sounds_dir, "scenario_end.wav")

    make_player(sounds_dir, output).play(SoundEvent.SCENARIO_END)

    assert output.files == [path]


def test_without_its_own_file_the_end_of_a_scenario_plays_the_work_sound(sounds_dir, output):
    path = put(sounds_dir, "work_end.wav")
    put(sounds_dir, "break_end.wav")

    make_player(sounds_dir, output).play(SoundEvent.SCENARIO_END)

    assert output.files == [path]


def test_the_work_sound_does_not_fall_back_to_the_scenario_sound(sounds_dir, output):
    put(sounds_dir, "scenario_end.wav")

    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.plays == []


def test_the_end_of_a_scenario_is_silent_without_any_of_the_files(sounds_dir, output):
    make_player(sounds_dir, output).play(SoundEvent.SCENARIO_END)

    assert output.plays == []


@pytest.mark.parametrize("extension", ["wav", "ogg", "flac", "mp3"])
def test_every_format_is_played(sounds_dir, output, extension):
    path = put(sounds_dir, f"work_end.{extension}")

    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.files == [path]


def test_the_formats_are_preferred_in_the_order_wav_ogg_flac_mp3(sounds_dir, output):
    put(sounds_dir, "work_end.mp3")
    put(sounds_dir, "work_end.flac")
    ogg = put(sounds_dir, "work_end.ogg")

    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.files == [ogg]


def test_a_missing_file_means_no_sound(sounds_dir, output):
    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.plays == []


def test_a_missing_directory_means_no_sound(tmp_path, output):
    make_player(tmp_path / "nowhere", output).play(SoundEvent.WORK_END)

    assert output.plays == []


def test_a_file_that_cannot_be_played_does_not_stop_the_next_format_from_trying(
    sounds_dir,
):
    class PlaysOnlyOgg:
        def __init__(self):
            self.tried = []

        def play(self, file, *, loop=False):
            self.tried.append(file.name)
            return object() if file.suffix == ".ogg" else None

    wav = put(sounds_dir, "work_end.wav")
    ogg = put(sounds_dir, "work_end.ogg")
    output = PlaysOnlyOgg()

    make_player(sounds_dir, output).play(SoundEvent.WORK_END)

    assert output.tried == [wav.name, ogg.name]


def test_no_sound_system_means_no_sound_and_no_error(sounds_dir, silent_output):
    put(sounds_dir, "work_end.wav")

    make_player(sounds_dir, silent_output).play(SoundEvent.WORK_END)

    assert len(silent_output.plays) == 1  # it was tried; nothing came of it


def test_the_sounds_of_the_application_are_in_its_package():
    import fermata.sound

    assert (Path(fermata.sound.__file__).parent / "sounds").is_dir()


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

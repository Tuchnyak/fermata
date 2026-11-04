import pytest
from timer.arguments import Arguments, parse_arguments
from timer.version import app_version


def test_a_run_from_source_has_no_real_time_by_default():
    assert parse_arguments([], release=False) == Arguments(real_time=False)


def test_real_time_can_be_asked_for_in_a_run_from_source():
    assert parse_arguments(["--real-time"], release=False) == Arguments(real_time=True)


def test_a_release_has_no_real_time_option():
    with pytest.raises(SystemExit):
        parse_arguments(["--real-time"], release=True)


def test_a_release_runs_without_arguments():
    assert parse_arguments([], release=True) == Arguments(real_time=False)


@pytest.mark.parametrize("release", [False, True])
def test_unknown_options_are_refused(release):
    with pytest.raises(SystemExit):
        parse_arguments(["--nonsense"], release=release)


@pytest.mark.parametrize("release", [False, True])
def test_version_prints_the_name_and_the_version_and_stops(capsys, release):
    with pytest.raises(SystemExit) as stop:
        parse_arguments(["--version"], release=release)

    assert stop.value.code == 0
    assert capsys.readouterr().out == f"timer {app_version()}\n"

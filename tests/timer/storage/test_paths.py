import sys

import pytest
from timer.storage.paths import data_dir, db_path


@pytest.fixture(autouse=True)
def no_data_dir_override(monkeypatch):
    monkeypatch.delenv("TIMER_DATA_DIR", raising=False)


@pytest.fixture
def release_build(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)


@pytest.fixture
def source_build(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)


# --- the directory of a release build -----------------------------------------


def test_a_release_uses_the_timer_directory_in_xdg_data_home(
    release_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert data_dir() == tmp_path / "xdg" / "timer"


def test_a_release_defaults_to_local_share_in_home(
    release_build, monkeypatch, tmp_path
):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer"


# --- the directory when running from source (development) ----------------------


def test_running_from_source_uses_the_timer_dev_directory_in_xdg_data_home(
    source_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert data_dir() == tmp_path / "xdg" / "timer-dev"


def test_running_from_source_defaults_to_local_share_in_home(
    source_build, monkeypatch, tmp_path
):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer-dev"


def test_the_two_builds_never_share_a_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    release_dir = data_dir()
    monkeypatch.delattr(sys, "frozen")
    source_dir = data_dir()

    assert release_dir != source_dir


# --- XDG_DATA_HOME that must be ignored ----------------------------------------


@pytest.mark.parametrize("xdg_data_home", ["", "relative/dir"])
def test_an_empty_or_relative_xdg_data_home_is_ignored(
    source_build, monkeypatch, tmp_path, xdg_data_home
):
    monkeypatch.setenv("XDG_DATA_HOME", xdg_data_home)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer-dev"


# --- TIMER_DATA_DIR ------------------------------------------------------------


@pytest.mark.parametrize("build", ["release_build", "source_build"])
def test_timer_data_dir_is_used_as_it_is_in_either_build(
    request, build, monkeypatch, tmp_path
):
    request.getfixturevalue(build)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("TIMER_DATA_DIR", str(tmp_path / "scratch"))

    assert data_dir() == tmp_path / "scratch"


@pytest.mark.parametrize("override", ["", "relative/dir"])
def test_an_empty_or_relative_timer_data_dir_is_ignored(
    source_build, monkeypatch, tmp_path, override
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("TIMER_DATA_DIR", override)

    assert data_dir() == tmp_path / "timer-dev"


# --- creating the directory ------------------------------------------------------


def test_the_directory_is_created_with_parents(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "missing" / "xdg"))

    assert data_dir().is_dir()


def test_the_directory_of_timer_data_dir_is_created_with_parents(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("TIMER_DATA_DIR", str(tmp_path / "missing" / "scratch"))

    assert data_dir().is_dir()


def test_the_directory_can_be_asked_for_again(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert data_dir() == data_dir()


# --- the database file -----------------------------------------------------------


def test_the_database_is_timer_db_in_the_data_dir(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert db_path() == tmp_path / "timer-dev" / "timer.db"

import sys
from pathlib import Path

import pytest
from fermata.storage.paths import data_dir, db_path


@pytest.fixture(autouse=True)
def no_data_dir_override(monkeypatch):
    monkeypatch.delenv("FERMATA_DATA_DIR", raising=False)


@pytest.fixture(autouse=True)
def linux(monkeypatch):
    """The tests run on the platform they name, whatever machine they run on."""
    monkeypatch.setattr(sys, "platform", "linux")


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")


@pytest.fixture
def home(monkeypatch, tmp_path):
    """The home directory of the user; `HOME` means nothing on Windows."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def release_build(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)


@pytest.fixture
def source_build(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)


# --- the directory of a release build -----------------------------------------


def test_a_release_uses_the_fermata_directory_in_xdg_data_home(
    release_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert data_dir() == tmp_path / "xdg" / "fermata"


def test_a_release_defaults_to_local_share_in_home(release_build, monkeypatch, home, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    assert data_dir() == tmp_path / ".local" / "share" / "fermata"


# --- the directory when running from source (development) ----------------------


def test_running_from_source_uses_the_fermata_dev_directory_in_xdg_data_home(
    source_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert data_dir() == tmp_path / "xdg" / "fermata-dev"


def test_running_from_source_defaults_to_local_share_in_home(
    source_build, monkeypatch, home, tmp_path
):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    assert data_dir() == tmp_path / ".local" / "share" / "fermata-dev"


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
    source_build, monkeypatch, home, tmp_path, xdg_data_home
):
    monkeypatch.setenv("XDG_DATA_HOME", xdg_data_home)

    assert data_dir() == tmp_path / ".local" / "share" / "fermata-dev"


# --- FERMATA_DATA_DIR ------------------------------------------------------------


@pytest.mark.parametrize("build", ["release_build", "source_build"])
def test_fermata_data_dir_is_used_as_it_is_in_either_build(
    request, build, monkeypatch, tmp_path
):
    request.getfixturevalue(build)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("FERMATA_DATA_DIR", str(tmp_path / "scratch"))

    assert data_dir() == tmp_path / "scratch"


@pytest.mark.parametrize("override", ["", "relative/dir"])
def test_an_empty_or_relative_fermata_data_dir_is_ignored(
    source_build, monkeypatch, tmp_path, override
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("FERMATA_DATA_DIR", override)

    assert data_dir() == tmp_path / "fermata-dev"


# --- creating the directory ------------------------------------------------------


def test_the_directory_is_created_with_parents(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "missing" / "xdg"))

    assert data_dir().is_dir()


def test_the_directory_of_timer_data_dir_is_created_with_parents(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("FERMATA_DATA_DIR", str(tmp_path / "missing" / "scratch"))

    assert data_dir().is_dir()


def test_the_directory_can_be_asked_for_again(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert data_dir() == data_dir()


# --- the database file -----------------------------------------------------------


def test_the_database_is_fermata_db_in_the_data_dir(source_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert db_path() == tmp_path / "fermata-dev" / "fermata.db"


# --- the directory on Windows ----------------------------------------------------


def test_a_release_on_windows_uses_the_fermata_directory_in_local_app_data(
    windows, release_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    assert data_dir() == tmp_path / "local" / "fermata"


def test_running_from_source_on_windows_uses_the_fermata_dev_directory(
    windows, source_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    assert data_dir() == tmp_path / "local" / "fermata-dev"


@pytest.mark.parametrize("local_app_data", ["", "relative/dir"])
def test_an_empty_or_relative_local_app_data_falls_back_to_the_user_profile(
    windows, release_build, monkeypatch, home, tmp_path, local_app_data
):
    monkeypatch.setenv("LOCALAPPDATA", local_app_data)

    assert data_dir() == tmp_path / "AppData" / "Local" / "fermata"


def test_a_missing_local_app_data_falls_back_to_the_user_profile(
    windows, release_build, monkeypatch, home, tmp_path
):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert data_dir() == tmp_path / "AppData" / "Local" / "fermata"


def test_xdg_data_home_means_nothing_on_windows(windows, release_build, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    assert data_dir() == tmp_path / "local" / "fermata"


def test_fermata_data_dir_is_used_as_it_is_on_windows(windows, monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("FERMATA_DATA_DIR", str(tmp_path / "scratch"))

    assert data_dir() == tmp_path / "scratch"


def test_the_database_on_windows_is_fermata_db_in_the_data_dir(
    windows, release_build, monkeypatch, tmp_path
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    assert db_path() == tmp_path / "local" / "fermata" / "fermata.db"

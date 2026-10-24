from timer.storage.paths import data_dir, db_path


def test_data_dir_uses_xdg_data_home_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    assert data_dir() == tmp_path / "xdg" / "timer"


def test_data_dir_defaults_to_local_share_in_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer"


def test_data_dir_ignores_empty_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", "")
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer"


def test_data_dir_ignores_relative_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", "relative/dir")
    monkeypatch.setenv("HOME", str(tmp_path))

    assert data_dir() == tmp_path / ".local" / "share" / "timer"


def test_data_dir_is_created_with_parents(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "missing" / "xdg"))

    assert data_dir().is_dir()


def test_data_dir_can_be_called_again(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert data_dir() == data_dir()


def test_db_path_is_timer_db_in_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert db_path() == tmp_path / "timer" / "timer.db"

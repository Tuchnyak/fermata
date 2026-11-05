import os
import sys
from pathlib import Path

from fermata.build import is_release


def data_dir() -> Path:
    """The directory of the database.

    A release and a run from source use different directories, so development never touches
    the data of an installed release. `FERMATA_DATA_DIR` overrides both.
    """
    override = os.environ.get("FERMATA_DATA_DIR", "")
    if os.path.isabs(override):
        path = Path(override)
    else:
        path = _base_dir() / ("fermata" if is_release() else "fermata-dev")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _base_dir() -> Path:
    """Where the user's program data goes: `%LOCALAPPDATA%` on Windows (local, the database must
    not roam), `$XDG_DATA_HOME` elsewhere; a value that is not an absolute path is ignored."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) if os.path.isabs(local) else Path.home() / "AppData" / "Local"
    xdg = os.environ.get("XDG_DATA_HOME", "")
    return Path(xdg) if os.path.isabs(xdg) else Path.home() / ".local" / "share"


def db_path() -> Path:
    return data_dir() / "fermata.db"

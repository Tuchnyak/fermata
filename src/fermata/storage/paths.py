import os
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
        xdg = os.environ.get("XDG_DATA_HOME", "")
        base = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".local" / "share"
        path = base / ("fermata" if is_release() else "fermata-dev")
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "fermata.db"

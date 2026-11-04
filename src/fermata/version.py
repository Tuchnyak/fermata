"""The version of the application: the one in `pyproject.toml`, read from the package metadata.

The number is written nowhere else. PyInstaller sees the call below and puts the metadata into
the built executable, which is checked by running it with `--version`.
"""

from importlib.metadata import version


def app_version() -> str:
    return version("fermata-timer")

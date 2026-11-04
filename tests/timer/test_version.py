import tomllib
from pathlib import Path

from timer.version import app_version

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def test_the_version_is_the_one_of_pyproject():
    written = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]

    assert app_version() == written

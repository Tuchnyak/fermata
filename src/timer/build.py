"""What kind of build is running: a release or the sources under development."""

import sys


def is_release() -> bool:
    """A release is the frozen executable; `uv run timer` runs from source."""
    return bool(getattr(sys, "frozen", False))

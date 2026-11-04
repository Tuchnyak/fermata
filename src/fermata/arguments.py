"""The command line of the application."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from fermata.version import app_version


@dataclass(frozen=True)
class Arguments:
    real_time: bool  # development only: the clock goes at the normal speed


def parse_arguments(argv: Sequence[str] | None = None, *, release: bool) -> Arguments:
    parser = argparse.ArgumentParser(prog="timer")
    parser.add_argument("--version", action="version", version=f"timer {app_version()}")
    if not release:
        parser.add_argument(
            "--real-time",
            action="store_true",
            help="run the clock at the normal speed (a run from source goes faster)",
        )
    parsed = vars(parser.parse_args(argv))
    return Arguments(real_time=parsed.get("real_time", False))

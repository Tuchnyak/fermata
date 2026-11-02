"""Sound notifications: which sound an engine event calls for, and playing it.

The sounds are files in `sounds/` next to this module, `work_end.<ext>` and `break_end.<ext>`.
They are played by a system command in the background (no audio library is needed), and
anything that goes wrong, such as no file or no player, only means there is no sound.
"""

import shutil
import subprocess
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from timer.engine import FlowEvent
from timer.intervals import IntervalKind, IntervalStatus
from timer.storage.settings import Settings

SOUNDS_DIR = Path(__file__).parent / "sounds"

# The formats of the files, the best first.
EXTENSIONS = ("wav", "ogg", "flac", "mp3")

# The players in the order they are tried: the program, its options and the formats it plays.
PLAYERS = (
    ("paplay", (), frozenset({"wav", "ogg", "flac"})),
    ("pw-play", (), frozenset({"wav", "ogg", "flac"})),
    (
        "ffplay",
        ("-nodisp", "-autoexit", "-loglevel", "quiet"),
        frozenset({"wav", "ogg", "flac", "mp3"}),
    ),
    ("aplay", (), frozenset({"wav"})),
)


class SoundEvent(StrEnum):
    """What a sound is for; the value is the name of its file."""

    WORK_END = "work_end"
    BREAK_END = "break_end"


def sound_event_for(event: FlowEvent) -> SoundEvent | None:
    """The sound an engine event calls for: an interval that ended by time. An interval ended
    by the user (skipped or stopped) is silent."""
    finished = event.finished_interval
    if finished is None or finished.status != IntervalStatus.COMPLETED:
        return None
    if finished.kind == IntervalKind.WORK:
        return SoundEvent.WORK_END
    return SoundEvent.BREAK_END


class SoundPlayer:
    def __init__(
        self,
        sounds_dir: Path = SOUNDS_DIR,
        which: Callable[[str], str | None] = shutil.which,
        launch: Callable[..., subprocess.Popen] = subprocess.Popen,
    ):
        self._sounds_dir = sounds_dir
        self._which = which
        self._launch = launch
        self._running: list[subprocess.Popen] = []

    def play(self, sound: SoundEvent) -> None:
        for extension in EXTENSIONS:
            file = self._sounds_dir / f"{sound}.{extension}"
            if not file.is_file():
                continue
            command = self._command_for(file, extension)
            if command is not None:
                self._start(command)
                return

    def _command_for(self, file: Path, extension: str) -> list[str] | None:
        for program, options, formats in PLAYERS:
            if extension not in formats:
                continue
            path = self._which(program)
            if path is not None:
                return [path, *options, str(file)]
        return None

    def _start(self, command: list[str]) -> None:
        # A finished player stays a zombie until it is asked how it ended.
        self._running = [process for process in self._running if process.poll() is None]
        try:
            process = self._launch(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return
        self._running.append(process)


class SoundNotifier:
    """The listener of the engine's events that plays their sounds while sound is on."""

    def __init__(self, get_settings: Callable[[], Settings], player: SoundPlayer):
        self._get_settings = get_settings
        self._player = player

    def __call__(self, event: FlowEvent) -> None:
        sound = sound_event_for(event)
        if sound is not None and self._get_settings().sound:
            self._player.play(sound)

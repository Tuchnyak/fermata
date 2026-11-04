"""Sound notifications: which sound an engine event calls for, and playing it.

The sounds are files in `sounds/` next to this module: `work_end.<ext>`, `break_end.<ext>` and
`scenario_end.<ext>`, which `work_end` stands in for while it is missing.
They are played inside the program (see `audio.py`), and anything that goes wrong, such as no
file or no sound system, only means there is no sound.
"""

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from fermata.audio import AudioOutput
from fermata.engine import FlowEvent
from fermata.intervals import IntervalKind, IntervalStatus
from fermata.storage.settings import Settings

SOUNDS_DIR = Path(__file__).parent / "sounds"

# The formats of the files, the best first.
EXTENSIONS = ("wav", "ogg", "flac", "mp3")


class SoundEvent(StrEnum):
    """What a sound is for; the value is the name of its file."""

    WORK_END = "work_end"
    BREAK_END = "break_end"
    SCENARIO_END = "scenario_end"


# The sound that plays when the file of a sound is missing.
FALLBACKS = {SoundEvent.SCENARIO_END: SoundEvent.WORK_END}


def sound_event_for(event: FlowEvent) -> SoundEvent | None:
    """The sound an engine event calls for: an interval that ended by time, or a scenario that
    ran to its end. An interval ended by the user (skipped or stopped) is silent."""
    finished = event.finished_interval
    if finished is None or finished.status != IntervalStatus.COMPLETED:
        return None
    if finished.kind == IntervalKind.WORK:
        return SoundEvent.SCENARIO_END if event.session_completed else SoundEvent.WORK_END
    return SoundEvent.BREAK_END


def sound_files(sounds_dir: Path, name: str) -> list[Path]:
    """The files that exist for a sound, the best format first."""
    files = []
    for extension in EXTENSIONS:
        file = sounds_dir / f"{name}.{extension}"
        if file.is_file():
            files.append(file)
    return files


class SoundPlayer:
    def __init__(self, sounds_dir: Path, output: AudioOutput):
        self._sounds_dir = sounds_dir
        self._output = output

    def play(self, sound: SoundEvent) -> None:
        files = sound_files(self._sounds_dir, sound)
        if not files and sound in FALLBACKS:
            files = sound_files(self._sounds_dir, FALLBACKS[sound])
        for file in files:
            if self._output.play(file) is not None:
                return


class SoundNotifier:
    """The listener of the engine's events that plays their sounds while sound is on."""

    def __init__(self, get_settings: Callable[[], Settings], player: SoundPlayer):
        self._get_settings = get_settings
        self._player = player

    def __call__(self, event: FlowEvent) -> None:
        sound = sound_event_for(event)
        if sound is not None and self._get_settings().sound:
            self._player.play(sound)

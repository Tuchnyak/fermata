"""The background sound of a work interval: ticking, white noise or rain, in a loop.

It plays while a work interval is running and is silent at every other time: idle, waiting for
confirmation, in a break, paused. The choice and the switch of the sounds are read at every
`update`, so a change applies at once. Only `ffplay` loops a file, so without it there is no
background sound; anything that goes wrong, such as no file or no player, only means silence.
`ffplay` is run by `timeout` (coreutils), because its own `-t` does not end a loop.
The files are in `sounds/` (see `sound.py`), named like the choices: `rain.wav`.
"""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from fermata.engine import Engine
from fermata.intervals import IntervalKind
from fermata.sound import SOUNDS_DIR, sound_files
from fermata.storage.settings import Settings

PLAYER = "ffplay"
OPTIONS = ("-nodisp", "-autoexit", "-loglevel", "quiet", "-loop", "0")
# The player is ended after the time left in the interval, plus this: if the application dies
# without stopping it, the sound does not play on for ever.
EXTRA_SECONDS = 5


class BackgroundSound:
    def __init__(
        self,
        engine: Engine,
        get_settings: Callable[[], Settings],
        sounds_dir: Path = SOUNDS_DIR,
        which: Callable[[str], str | None] = shutil.which,
        launch: Callable[..., subprocess.Popen] = subprocess.Popen,
    ):
        self._engine = engine
        self._get_settings = get_settings
        self._sounds_dir = sounds_dir
        self._which = which
        self._launch = launch
        self._wanted: str | None = None  # what has been started, even if nothing came of it
        self._process: subprocess.Popen | None = None

    def update(self) -> None:
        """Start, replace or stop the sound, as the timer and the settings now call for."""
        wanted = self._sound_called_for()
        if wanted == self._wanted:
            return
        self.stop()
        self._wanted = wanted
        if wanted is not None:
            self._start(wanted)

    def stop(self) -> None:
        self._wanted = None
        process, self._process = self._process, None
        if process is None:
            return
        process.terminate()
        try:
            process.wait(timeout=1)  # a finished player stays a zombie until it is waited for
        except subprocess.TimeoutExpired:
            process.kill()

    def _sound_called_for(self) -> str | None:
        settings = self._get_settings()
        interval = self._engine.current_interval
        if not settings.sound or settings.background_sound == "off":
            return None
        if interval is None or interval.kind != IntervalKind.WORK or self._engine.is_paused:
            return None
        return settings.background_sound

    def _start(self, name: str) -> None:
        files = sound_files(self._sounds_dir, name)
        player = self._which(PLAYER)
        limiter = self._which("timeout")
        if not files or player is None or limiter is None:
            return
        file, _extension = files[0]
        seconds = round(self._engine.remaining_seconds()) + EXTRA_SECONDS
        try:
            self._process = self._launch(
                [limiter, str(seconds), player, *OPTIONS, str(file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return

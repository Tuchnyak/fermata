"""Tells a panel the scale of its size whenever it changes (see scaling.py)."""

import tkinter
from collections.abc import Callable

from timer.ui.scaling import scale_for


class ScaleWatcher:
    def __init__(self, panel: tkinter.Misc, on_scale: Callable[[float], None]):
        """Call `on_scale` with the scale of the panel whenever its size changes it."""
        self._on_scale = on_scale
        self._scale: float | None = None
        panel.bind("<Configure>", self._on_configure)

    def _on_configure(self, event: tkinter.Event) -> None:
        scale = scale_for(event.width, event.height)
        if scale != self._scale:
            self._scale = scale
            self._on_scale(scale)

"""The settings screen: the timer values, the transition mode, the blink and sound flags and the theme.

Nothing is stored until the Save button is pressed, except the theme: it is applied and stored
as soon as it is chosen, so that its look can be seen while choosing.
"""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.storage.settings_rules import (
    LONG_BREAK_EVERY_RANGE,
    LONG_BREAK_MINUTES_RANGE,
    SHORT_BREAK_MINUTES_RANGE,
    TRANSITION_MODES,
    WORK_MINUTES_RANGE,
)
from timer.themes import ttk_theme_name
from timer.ui.number_slider import NumberSlider
from timer.ui.settings_view_model import SettingsViewModel

SLIDER_LENGTH = 320  # the same for every slider, whatever its range
MINUTES_STEP = 5  # the lowest time on a slider is one step, although the rules allow 1

# key, lowest, highest, step, the values written under the tick marks
NUMBER_FIELDS = (
    ("work_minutes", MINUTES_STEP, WORK_MINUTES_RANGE[1], MINUTES_STEP, (5, 30, 60, 90, 120)),
    (
        "short_break_minutes",
        MINUTES_STEP,
        SHORT_BREAK_MINUTES_RANGE[1],
        MINUTES_STEP,
        (5, 10, 15, 20, 25, 30),
    ),
    (
        "long_break_minutes",
        MINUTES_STEP,
        LONG_BREAK_MINUTES_RANGE[1],
        MINUTES_STEP,
        (5, 15, 30, 45, 60),
    ),
    (
        "long_break_every",
        LONG_BREAK_EVERY_RANGE[0],
        LONG_BREAK_EVERY_RANGE[1],
        1,
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    ),
)


class SettingsScreen(ttk.Frame):
    def __init__(
        self, parent: tkinter.Misc, view_model: SettingsViewModel, actions: ttk.Frame
    ):
        """`actions` is the place at the right of the window header for the screen's buttons."""
        super().__init__(parent)
        self._view_model = view_model
        self._sliders: dict[str, NumberSlider] = {}
        self._mode_variable = tkinter.StringVar()
        self._blink_variable = tkinter.BooleanVar()
        self._sound_variable = tkinter.BooleanVar()

        self._build_save_button(actions)
        self._build_number_fields()
        self._build_transition_modes()
        self._build_flags()
        self._build_theme()
        self._load_settings()

    def _build_save_button(self, actions: ttk.Frame) -> None:
        ttk.Button(
            actions,
            text=t("settings.save"),
            command=self._save,
            bootstyle="success",
            takefocus=False,
        ).pack(side="right")
        self._message = ttk.Label(actions)
        self._message.pack(side="right", padx=16)

    def _build_number_fields(self) -> None:
        grid = ttk.Frame(self)
        grid.pack(fill="x", pady=(0, 16))
        grid.columnconfigure(0, weight=1)  # the sliders are pressed to the right edge
        for row, (key, lowest, highest, step, labeled_values) in enumerate(NUMBER_FIELDS):
            ttk.Label(grid, text=t(f"settings.{key}")).grid(
                row=row, column=0, sticky="w", pady=6
            )
            slider = NumberSlider(
                grid, lowest, highest, step, labeled_values, SLIDER_LENGTH
            )
            slider.grid(row=row, column=1, sticky="e", pady=6)
            self._sliders[key] = slider

    def _build_transition_modes(self) -> None:
        ttk.Label(self, text=t("settings.transition_mode")).pack(anchor="w")
        for mode in TRANSITION_MODES:
            # Radio buttons and the check box do not take focus: Space on a focused one
            # would act on it as well as act as a hotkey.
            ttk.Radiobutton(
                self,
                text=t(f"settings.mode.{mode}.name"),
                value=mode,
                variable=self._mode_variable,
                takefocus=False,
            ).pack(anchor="w", padx=(16, 0), pady=(4, 0))
            ttk.Label(
                self,
                text=t(f"settings.mode.{mode}.description"),
                wraplength=520,
            ).pack(anchor="w", padx=(40, 0))

    def _build_flags(self) -> None:
        for key, variable in (
            ("settings.blink", self._blink_variable),
            ("settings.sound", self._sound_variable),
        ):
            ttk.Checkbutton(
                self, text=t(key), variable=variable, takefocus=False
            ).pack(anchor="w", pady=(16, 0))

    def _build_theme(self) -> None:
        line = ttk.Frame(self)
        line.pack(anchor="w", pady=(16, 0))
        ttk.Label(line, text=t("settings.theme")).pack(side="left", padx=(0, 8))
        self._themes = self._view_model.themes()
        self._theme_selector = ttk.Combobox(
            line, values=[name for _, name in self._themes], state="readonly"
        )
        self._theme_selector.pack(side="left")
        self._theme_selector.bind("<<ComboboxSelected>>", self._on_theme_selected)

    def _on_theme_selected(self, event: tkinter.Event) -> None:
        theme_id, _ = self._themes[self._theme_selector.current()]
        message = self._view_model.choose_theme(theme_id)
        if message is not None:
            self._message.configure(text=message, bootstyle="danger")
            return
        ttk.Style().theme_use(ttk_theme_name(theme_id))
        for slider in self._sliders.values():
            slider.refresh_colors()  # what is drawn by hand does not follow the theme itself
        self.focus_set()

    def _load_settings(self) -> None:
        settings = self._view_model.settings()
        for key, slider in self._sliders.items():
            slider.set(getattr(settings, key))
        self._mode_variable.set(settings.transition_mode)
        self._blink_variable.set(settings.blink)
        self._sound_variable.set(settings.sound)
        for theme_id, name in self._themes:
            if theme_id == settings.theme:
                self._theme_selector.set(name)

    def _save(self) -> None:
        numbers = {}
        for key, slider in self._sliders.items():
            numbers[key] = slider.get()
        message = self._view_model.save(
            **numbers,
            transition_mode=self._mode_variable.get(),
            blink=self._blink_variable.get(),
            sound=self._sound_variable.get(),
        )
        if message is None:
            self._load_settings()  # shows the values as they were stored
            self._message.configure(text=t("settings.saved"), bootstyle="success")
        else:
            self._message.configure(text=message, bootstyle="danger")

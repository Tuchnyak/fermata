"""The settings screen: the timer values, the transition mode, the blink and sound flags, the
background sound, the theme and the language.

Nothing is stored until the Save button is pressed, except the background sound, the theme and
the language: they are applied and stored as soon as they are chosen, so that they can be heard
and seen while choosing. A new language redraws the screen, which gets back what was typed in
it but not saved yet (the draft).
"""

import tkinter
from collections.abc import Callable

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
from timer.ui.progress import faded
from timer.ui.settings_view_model import SettingsViewModel

VERSION_FONT_SIZE = 9
VERSION_FADE_AMOUNT = 0.35  # how far the version's color moves towards the background
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
        self,
        parent: tkinter.Misc,
        view_model: SettingsViewModel,
        actions: ttk.Frame,
        on_language_changed: Callable[[dict[str, object]], None],
        draft: dict[str, object] | None = None,
    ):
        """`actions` is the place at the right of the window header for the screen's buttons.

        `on_language_changed` is called with the draft of the form after the language was
        changed, to have the screen drawn again in it; `draft` is what a screen drawn before
        left, to be put back.
        """
        super().__init__(parent)
        self._view_model = view_model
        self._on_language_changed = on_language_changed
        self._sliders: dict[str, NumberSlider] = {}
        self._mode_variable = tkinter.StringVar()
        self._blink_variable = tkinter.BooleanVar()
        self._sound_variable = tkinter.BooleanVar()

        self._build_save_button(actions)
        self._build_version(actions)
        self._build_number_fields()
        self._build_transition_modes()
        self._build_flags()
        self._build_background_sound()
        self._build_theme()
        self._load_settings(draft)

    def _build_version(self, actions: ttk.Frame) -> None:
        """The version right after the title in the header, small and dim.

        It is in the header, not above the settings: the screen has no room for another line.
        """
        self._version = ttk.Label(
            actions.master,
            text=self._view_model.version_text(),
            font=("TkDefaultFont", VERSION_FONT_SIZE),
        )
        self._version.pack(side="left", before=actions)
        self._dim_version()

    def _dim_version(self) -> None:
        style = ttk.Style()
        self._version.configure(
            foreground=faded(
                style.lookup("TLabel", "foreground"),
                style.lookup("TFrame", "background"),
                VERSION_FADE_AMOUNT,
            )
        )

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

    def _build_background_sound(self) -> None:
        line = ttk.Frame(self)
        line.pack(anchor="w", pady=(16, 0))
        ttk.Label(line, text=t("settings.background_sound")).pack(side="left", padx=(0, 8))
        self._background_sounds = self._view_model.background_sounds()
        self._background_sound_selector = ttk.Combobox(
            line, values=[name for _, name in self._background_sounds], state="readonly"
        )
        self._background_sound_selector.pack(side="left")
        self._background_sound_selector.bind(
            "<<ComboboxSelected>>", self._on_background_sound_selected
        )

    def _on_background_sound_selected(self, event: tkinter.Event) -> None:
        sound_id, _ = self._background_sounds[self._background_sound_selector.current()]
        message = self._view_model.choose_background_sound(sound_id)
        if message is not None:
            self._message.configure(text=message, bootstyle="danger")
        self.focus_set()

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

        ttk.Label(line, text=t("settings.language")).pack(side="left", padx=(24, 8))
        self._languages = self._view_model.languages()
        self._language_selector = ttk.Combobox(
            line, values=[name for _, name in self._languages], state="readonly"
        )
        self._language_selector.pack(side="left")
        self._language_selector.bind("<<ComboboxSelected>>", self._on_language_selected)

    def _on_language_selected(self, event: tkinter.Event) -> None:
        language_id, _ = self._languages[self._language_selector.current()]
        message = self._view_model.choose_language(language_id)
        if message is not None:
            self._message.configure(text=message, bootstyle="danger")
            return
        self._on_language_changed(self._draft())

    def _draft(self) -> dict[str, object]:
        """What stands in the form now, saved or not."""
        draft: dict[str, object] = {}
        for key, slider in self._sliders.items():
            draft[key] = int(slider.get())
        draft["transition_mode"] = self._mode_variable.get()
        draft["blink"] = self._blink_variable.get()
        draft["sound"] = self._sound_variable.get()
        return draft

    def _on_theme_selected(self, event: tkinter.Event) -> None:
        theme_id, _ = self._themes[self._theme_selector.current()]
        message = self._view_model.choose_theme(theme_id)
        if message is not None:
            self._message.configure(text=message, bootstyle="danger")
            return
        ttk.Style().theme_use(ttk_theme_name(theme_id))
        for slider in self._sliders.values():
            slider.refresh_colors()  # what is drawn by hand does not follow the theme itself
        self._dim_version()
        self.focus_set()

    def _load_settings(self, draft: dict[str, object] | None = None) -> None:
        """Show the stored settings, with what a draft changes in them."""
        settings = self._view_model.settings()
        values = {**vars(settings), **(draft or {})}
        for key, slider in self._sliders.items():
            slider.set(values[key])
        self._mode_variable.set(values["transition_mode"])
        self._blink_variable.set(values["blink"])
        self._sound_variable.set(values["sound"])
        for theme_id, name in self._themes:
            if theme_id == settings.theme:
                self._theme_selector.set(name)
        for sound_id, name in self._background_sounds:
            if sound_id == settings.background_sound:
                self._background_sound_selector.set(name)
        for language_id, name in self._languages:
            if language_id == settings.language:
                self._language_selector.set(name)

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

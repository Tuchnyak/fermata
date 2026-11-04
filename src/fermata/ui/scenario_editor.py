"""The scenario editor: name, rows, repeat count, live preview and the timer overrides.

The state lives in the view model; the widgets write what is typed into it and redraw the
preview. The buttons that end the editing are put into the place at the right of the window
header, like the Save button of the settings screen.
"""

import tkinter
from collections.abc import Callable
from functools import partial

import ttkbootstrap as ttk
from fermata.i18n import t
from fermata.scenarios import REPEAT_COUNT_RANGE, ROW_COUNT_RANGE
from fermata.storage.settings_rules import (
    LONG_BREAK_EVERY_RANGE,
    LONG_BREAK_MINUTES_RANGE,
    SHORT_BREAK_MINUTES_RANGE,
    WORK_MINUTES_RANGE,
)
from fermata.ui.progress_row import ProgressRow
from fermata.ui.scenario_editor_view_model import RowDraft, ScenarioEditorViewModel

SWATCH_SIZE = 16
COUNT_WIDTH = 4

# setting, its limits, the step of the arrow buttons of its field
OVERRIDE_INPUTS = (
    ("work_minutes", WORK_MINUTES_RANGE, 5),
    ("short_break_minutes", SHORT_BREAK_MINUTES_RANGE, 5),
    ("long_break_minutes", LONG_BREAK_MINUTES_RANGE, 5),
    ("long_break_every", LONG_BREAK_EVERY_RANGE, 1),
)


class ScenarioEditor(ttk.Frame):
    def __init__(
        self,
        parent: tkinter.Misc,
        view_model: ScenarioEditorViewModel,
        actions: ttk.Frame,
        can_start: bool,
        on_close: Callable[[], None],
        on_start: Callable[[int], None],
    ):
        """`actions` is the place at the right of the window header for the buttons.

        `on_close` is called when the editing ends without starting, `on_start` with the id
        of the saved scenario when it ends with Save & start.
        """
        super().__init__(parent)
        self._view_model = view_model
        self._on_close = on_close
        self._on_start = on_start
        self._background = ttk.Style().lookup("TFrame", "background")
        self._categories = view_model.categories()

        self._build_buttons(actions, can_start)
        self._build_name()
        self._rows_frame = ttk.Frame(self)
        self._rows_frame.pack(fill="x", pady=(12, 0))
        self._build_add_row()
        self._build_repeat()
        self._build_preview()
        self._build_overrides()
        self._error = ttk.Label(self, bootstyle="danger")
        self._error.pack(fill="x", pady=(8, 0))

        self._rebuild_rows()
        self._refresh_preview()

    # --- building -------------------------------------------------------------------

    def _build_buttons(self, actions: ttk.Frame, can_start: bool) -> None:
        # Right to left: the first packed is the rightmost.
        ttk.Button(
            actions,
            text=t("scenarios.editor.save_and_start"),
            command=partial(self._save, start=True),
            bootstyle="success",
            takefocus=False,
            state="normal" if can_start else "disabled",
        ).pack(side="right")
        ttk.Button(
            actions,
            text=t("scenarios.editor.save"),
            command=partial(self._save, start=False),
            bootstyle="success-outline",
            takefocus=False,
        ).pack(side="right", padx=8)
        ttk.Button(
            actions,
            text=t("scenarios.editor.cancel"),
            command=self._on_close,
            takefocus=False,
        ).pack(side="right")

    def _build_name(self) -> None:
        line = ttk.Frame(self)
        line.pack(fill="x")
        ttk.Label(line, text=t("scenarios.editor.name")).pack(side="left")
        self._name_variable = tkinter.StringVar(value=self._view_model.name())
        self._name_variable.trace_add("write", self._on_name_changed)
        ttk.Entry(line, textvariable=self._name_variable).pack(
            side="left", fill="x", expand=True, padx=8
        )

    def _build_add_row(self) -> None:
        ttk.Button(
            self,
            text=t("scenarios.editor.add_row"),
            command=self._add_row,
            takefocus=False,
        ).pack(anchor="w", pady=(8, 0))

    def _build_repeat(self) -> None:
        line = ttk.Frame(self)
        line.pack(fill="x", pady=(12, 0))
        ttk.Label(line, text=t("scenarios.editor.repeat")).pack(side="left")
        self._repeat_variable = tkinter.StringVar(
            value=str(self._view_model.repeat_count())
        )
        self._repeat_variable.trace_add("write", self._on_repeat_changed)
        ttk.Spinbox(
            line,
            from_=REPEAT_COUNT_RANGE[0],
            to=REPEAT_COUNT_RANGE[1],
            textvariable=self._repeat_variable,
            width=COUNT_WIDTH,
        ).pack(side="left", padx=8)
        ttk.Label(line, text=t("scenarios.editor.repeat_suffix")).pack(side="left")

    def _build_preview(self) -> None:
        self._progress_row = ProgressRow(self)
        self._progress_row.pack(fill="x", pady=(16, 0))
        self._preview_text = ttk.Label(self)
        self._preview_text.pack(anchor="w", pady=(4, 0))

    def _build_overrides(self) -> None:
        overrides = self._view_model.overrides()
        has_overrides = any(value is not None for value in overrides.values())

        self._overrides_open = tkinter.BooleanVar(value=has_overrides)
        ttk.Checkbutton(
            self,
            text=t("scenarios.editor.timer_settings"),
            variable=self._overrides_open,
            command=self._toggle_overrides,
            takefocus=False,
        ).pack(anchor="w", pady=(16, 0))
        self._overrides_frame = ttk.Frame(self)
        self._override_switches: dict[str, tkinter.BooleanVar] = {}
        self._override_fields: dict[str, ttk.Spinbox] = {}
        self._override_values: dict[str, tkinter.StringVar] = {}
        global_settings = self._view_model.global_settings()
        for row, (field_name, (lowest, highest), step) in enumerate(OVERRIDE_INPUTS):
            override = overrides[field_name]
            switch = tkinter.BooleanVar(value=override is not None)
            self._override_switches[field_name] = switch
            ttk.Checkbutton(
                self._overrides_frame,
                text=t(f"settings.{field_name}"),
                variable=switch,
                command=partial(self._toggle_override, field_name),
                takefocus=False,
            ).grid(row=row, column=0, sticky="w", pady=2)

            shown = override if override is not None else getattr(global_settings, field_name)
            value = tkinter.StringVar(value=str(shown))
            field = ttk.Spinbox(
                self._overrides_frame,
                from_=lowest,
                to=highest,
                increment=step,
                textvariable=value,
                width=COUNT_WIDTH,
                state="normal" if override is not None else "disabled",
            )
            field.grid(row=row, column=1, sticky="e", padx=(16, 0), pady=2)
            value.trace_add("write", partial(self._on_override_typed, field_name, value))
            self._override_fields[field_name] = field
            self._override_values[field_name] = value
        self._overrides_frame.columnconfigure(0, weight=1)
        self._toggle_overrides()

    # --- the rows -------------------------------------------------------------------

    def _rebuild_rows(self) -> None:
        for child in self._rows_frame.winfo_children():
            child.destroy()
        ttk.Label(self._rows_frame, text=t("scenarios.editor.category")).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(self._rows_frame, text=t("scenarios.editor.intervals")).grid(
            row=0, column=3, sticky="w", padx=8
        )
        for index, row in enumerate(self._view_model.rows(), start=0):
            self._build_row(index, row)

    def _build_row(self, index: int, row: RowDraft) -> None:
        grid_row = index + 1
        frame = self._rows_frame
        ttk.Label(frame, text=str(index + 1), width=2).grid(row=grid_row, column=0, pady=2)

        swatch = tkinter.Canvas(
            frame,
            width=SWATCH_SIZE,
            height=SWATCH_SIZE,
            background=self._background,
            highlightthickness=0,
        )
        swatch.grid(row=grid_row, column=1, padx=(0, 8))
        self._paint_swatch(swatch, row.category_id)

        selector = ttk.Combobox(
            frame,
            values=[category.name for category in self._categories],
            state="readonly",
        )
        selector.set(self._category_name(row.category_id))
        selector.grid(row=grid_row, column=2, sticky="w")
        selector.bind(
            "<<ComboboxSelected>>", partial(self._on_category_selected, index, selector, swatch)
        )

        count_variable = tkinter.StringVar(value=str(row.count))
        count_variable.trace_add("write", partial(self._on_count_changed, index, count_variable))
        ttk.Spinbox(
            frame,
            from_=ROW_COUNT_RANGE[0],
            to=ROW_COUNT_RANGE[1],
            textvariable=count_variable,
            width=COUNT_WIDTH,
        ).grid(row=grid_row, column=3, padx=8)

        for column, (key, command) in enumerate(
            (
                ("scenarios.editor.move_up", partial(self._move_row_up, index)),
                ("scenarios.editor.move_down", partial(self._move_row_down, index)),
                ("scenarios.editor.remove_row", partial(self._remove_row, index)),
            ),
            start=4,
        ):
            ttk.Button(
                frame, text=t(key), command=command, width=3, takefocus=False
            ).grid(row=grid_row, column=column, padx=2)

    def _paint_swatch(self, swatch: tkinter.Canvas, category_id: int) -> None:
        color = next(c.color for c in self._categories if c.id == category_id)
        swatch.delete("all")
        swatch.create_oval(1, 1, SWATCH_SIZE - 1, SWATCH_SIZE - 1, fill=color, outline="")

    def _category_name(self, category_id: int) -> str:
        return next(c.name for c in self._categories if c.id == category_id)

    # --- reacting to changes --------------------------------------------------------

    def _on_name_changed(self, *_: str) -> None:
        self._view_model.set_name(self._name_variable.get())

    def _on_repeat_changed(self, *_: str) -> None:
        self._view_model.set_repeat_count(self._repeat_variable.get())
        self._refresh_preview()

    def _on_count_changed(self, index: int, variable: tkinter.StringVar, *_: str) -> None:
        self._view_model.set_row_count(index, variable.get())
        self._refresh_preview()

    def _on_category_selected(
        self, index: int, selector: ttk.Combobox, swatch: tkinter.Canvas, event: tkinter.Event
    ) -> None:
        category = self._categories[selector.current()]
        self._view_model.set_row_category(index, category.id)
        self._paint_swatch(swatch, category.id)
        self._refresh_preview()
        self.focus_set()  # the selector must not keep Space for its list

    def _add_row(self) -> None:
        self._view_model.add_row()
        self._rebuild_rows()
        self._refresh_preview()

    def _remove_row(self, index: int) -> None:
        self._view_model.remove_row(index)
        self._rebuild_rows()
        self._refresh_preview()

    def _move_row_up(self, index: int) -> None:
        self._view_model.move_row_up(index)
        self._rebuild_rows()
        self._refresh_preview()

    def _move_row_down(self, index: int) -> None:
        self._view_model.move_row_down(index)
        self._rebuild_rows()
        self._refresh_preview()

    def _toggle_overrides(self) -> None:
        if self._overrides_open.get():
            self._overrides_frame.pack(fill="x", padx=(24, 0))
        else:
            self._overrides_frame.pack_forget()

    def _toggle_override(self, field_name: str) -> None:
        field = self._override_fields[field_name]
        if self._override_switches[field_name].get():
            field.configure(state="normal")
            self._on_override_typed(field_name, self._override_values[field_name])
        else:
            field.configure(state="disabled")
            self._view_model.set_override(field_name, None)
            self._refresh_preview()

    def _on_override_typed(
        self, field_name: str, value: tkinter.StringVar, *_: str
    ) -> None:
        # While the field is switched off its value is only what the global setting shows.
        if not self._override_switches[field_name].get():
            return
        try:
            number = int(value.get())
        except ValueError:
            return  # half-typed text; the last whole number stays
        self._view_model.set_override(field_name, number)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self._view_model.preview()
        self._progress_row.show(preview.items)
        self._preview_text.configure(text=preview.text)

    def _save(self, start: bool) -> None:
        message = self._view_model.save()
        if message is not None:
            self._error.configure(text=message)
            return
        scenario_id = self._view_model.saved_scenario_id
        assert scenario_id is not None
        if start:
            self._on_start(scenario_id)
        else:
            self._on_close()

"""The scenarios screen: the list of saved scenarios, and the editor that replaces it while
one is created or changed."""

import tkinter
from collections.abc import Callable
from functools import partial

import ttkbootstrap as ttk
from timer.i18n import t
from timer.scenarios import ScenarioEntity
from timer.ui.scenario_editor import ScenarioEditor
from timer.ui.scenarios_view_model import ScenariosViewModel
from ttkbootstrap.dialogs import Messagebox


class ScenariosScreen(ttk.Frame):
    def __init__(
        self,
        parent: tkinter.Misc,
        view_model: ScenariosViewModel,
        actions: ttk.Frame,
        on_started: Callable[[], None],
    ):
        """`actions` is the place at the right of the window header for the editor's buttons.

        `on_started` is called after a scenario has been started.
        """
        super().__init__(parent)
        self._view_model = view_model
        self._actions = actions
        self._on_started = on_started
        self._show_list()

    def _clear(self) -> None:
        for frame in (self, self._actions):
            for child in frame.winfo_children():
                child.destroy()

    def _show_list(self) -> None:
        self._clear()
        ttk.Button(
            self, text=t("scenarios.new"), command=self._new, takefocus=False
        ).pack(anchor="e", pady=(0, 12))

        scenarios = self._view_model.scenarios()
        if not scenarios:
            ttk.Label(self, text=t("scenarios.empty")).pack(anchor="w")
        for scenario in scenarios:
            self._build_row(scenario)

    def _build_row(self, scenario: ScenarioEntity) -> None:
        row = ttk.Frame(self)
        row.pack(fill="x", pady=4)
        texts = ttk.Frame(row)
        texts.pack(side="left", fill="x", expand=True)
        ttk.Label(texts, text=scenario.name, font=("TkDefaultFont", 12)).pack(anchor="w")
        ttk.Label(texts, text=self._view_model.describe(scenario)).pack(anchor="w")

        buttons = (
            (t("scenarios.start"), self._start, self._view_model.can_start(), "success"),
            (t("scenarios.edit"), self._edit, True, None),
            (t("scenarios.delete"), self._delete, True, None),
        )
        for text, command, enabled, style in buttons:
            options = {"bootstyle": style} if style else {}
            ttk.Button(
                row,
                text=text,
                command=partial(command, scenario),
                takefocus=False,
                state="normal" if enabled else "disabled",
                **options,
            ).pack(side="left", padx=(8, 0))

    def _new(self) -> None:
        self._show_editor(self._view_model.new_editor())

    def _edit(self, scenario: ScenarioEntity) -> None:
        self._show_editor(self._view_model.editor_for(scenario.id))

    def _show_editor(self, editor) -> None:
        self._clear()
        ScenarioEditor(
            self,
            editor,
            self._actions,
            can_start=self._view_model.can_start(),
            on_close=self._show_list,
            on_start=self._save_and_start,
        ).pack(fill="both", expand=True)

    def _start(self, scenario: ScenarioEntity) -> None:
        self._save_and_start(scenario.id)

    def _save_and_start(self, scenario_id: int) -> None:
        self._view_model.start(scenario_id)
        self._on_started()

    def _delete(self, scenario: ScenarioEntity) -> None:
        answer = Messagebox.yesno(
            message=t("scenarios.delete_confirm", name=scenario.name),
            title=t("scenarios.delete"),
            parent=self,
            localize=False,
        )
        if answer == "Yes":
            self._view_model.delete(scenario.id)
            self._show_list()

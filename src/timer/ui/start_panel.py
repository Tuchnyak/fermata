"""The home screen while no session runs: two columns, Flow and Scenario, each with what to
start and its own Start button; after a scenario that ran to its end, how it went.

`Space` starts the kind last touched (a flow at first).
"""

import tkinter
from functools import partial

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.home_view_model import HomeViewModel, StartKind

COLUMN_GAP = 48
HEADING_FONT = ("TkDefaultFont", 20, "bold")
START_BUTTON_WIDTH = 14
START_BUTTON_STYLES = {StartKind.FLOW: "success-outline", StartKind.SCENARIO: "success"}


class StartPanel(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: HomeViewModel):
        super().__init__(parent)
        self._view_model = view_model
        view_model.preselect()
        self._categories = view_model.categories()
        self._scenarios = view_model.scenarios()

        center = ttk.Frame(self)
        center.pack(expand=True)

        summary = view_model.summary_text()
        if summary is not None:
            ttk.Label(center, text=summary, bootstyle="success").pack(pady=(0, 24))

        columns = ttk.Frame(center)
        columns.pack()
        self._build_flow_column(columns).grid(row=0, column=0, sticky="n")
        self._build_scenario_column(columns).grid(
            row=0, column=1, sticky="n", padx=(COLUMN_GAP, 0)
        )

    def _build_column(self, parent: ttk.Frame, heading_key: str) -> ttk.Frame:
        column = ttk.Frame(parent)
        ttk.Label(column, text=t(heading_key), font=HEADING_FONT).pack(anchor="w")
        ttk.Separator(column, bootstyle="success").pack(fill="x", pady=(4, 16))
        return column

    def _build_flow_column(self, parent: ttk.Frame) -> ttk.Frame:
        column = self._build_column(parent, "home.kind_flow")
        ttk.Label(column, text=t("home.category")).pack(anchor="w")
        selector = ttk.Combobox(
            column,
            values=[category.name for category in self._categories],
            state="readonly",
        )
        selector.set(self._view_model.selected_category().name)
        selector.pack(fill="x", pady=(4, 24))
        selector.bind("<<ComboboxSelected>>", self._on_category_selected)
        self._category_selector = selector
        self._add_start_button(column, StartKind.FLOW)
        return column

    def _build_scenario_column(self, parent: ttk.Frame) -> ttk.Frame:
        column = self._build_column(parent, "home.kind_scenario")
        ttk.Label(column, text=t("home.scenario_choice")).pack(anchor="w")
        selector = ttk.Combobox(
            column,
            values=[scenario.name for scenario in self._scenarios],
            state="readonly",
        )
        selected = self._view_model.selected_scenario()
        if selected is not None:
            selector.set(selected.name)
        selector.pack(fill="x", pady=(4, 24))
        selector.bind("<<ComboboxSelected>>", self._on_scenario_selected)
        self._scenario_selector = selector
        button = self._add_start_button(column, StartKind.SCENARIO)
        if selected is None:  # there is no scenario to start yet
            selector.configure(state="disabled")
            button.configure(state="disabled")
        return column

    def _add_start_button(self, column: ttk.Frame, kind: StartKind) -> ttk.Button:
        # The button does not take focus, so that Space on it is only the hotkey.
        button = ttk.Button(
            column,
            text=t("home.start"),
            command=partial(self._start, kind),
            width=START_BUTTON_WIDTH,
            bootstyle=START_BUTTON_STYLES[kind],
            takefocus=False,
        )
        button.pack()
        return button

    def _start(self, kind: StartKind) -> None:
        self._view_model.select_start_kind(kind)
        self._view_model.start()

    def _on_category_selected(self, event: tkinter.Event) -> None:
        index = self._category_selector.current()
        self._view_model.select(self._categories[index].id)
        self._view_model.select_start_kind(StartKind.FLOW)  # Space starts what was touched
        self._focus_away_from_selector()

    def _on_scenario_selected(self, event: tkinter.Event) -> None:
        index = self._scenario_selector.current()
        self._view_model.select_scenario(self._scenarios[index].id)
        self._view_model.select_start_kind(StartKind.SCENARIO)
        self._focus_away_from_selector()

    def _focus_away_from_selector(self) -> None:
        # With the focus in the selector, Space would open its list instead of starting.
        self.focus_set()

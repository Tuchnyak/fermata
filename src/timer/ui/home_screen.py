"""The home screen: the choice of a category and the Start button."""

import tkinter

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.home_view_model import HomeViewModel


class HomeScreen(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: HomeViewModel):
        super().__init__(parent)
        self._view_model = view_model
        view_model.preselect()
        self._categories = view_model.categories()

        center = ttk.Frame(self)
        center.pack(expand=True)

        ttk.Label(center, text=t("home.category")).pack(side="left")

        self._category_selector = ttk.Combobox(
            center,
            values=[category.name for category in self._categories],
            state="readonly",
        )
        selected_name = view_model.selected_category().name
        self._category_selector.set(selected_name)
        self._category_selector.pack(side="left", padx=8)
        self._category_selector.bind("<<ComboboxSelected>>", self._on_category_selected)

        # The button does not take focus, so that Space on it is only the hotkey.
        ttk.Button(
            center,
            text=t("home.start"),
            command=view_model.start,
            bootstyle="success",
            takefocus=False,
        ).pack(side="left", padx=(8, 0))

    def _on_category_selected(self, event: tkinter.Event) -> None:
        index = self._category_selector.current()
        self._view_model.select(self._categories[index].id)
        # Take the focus away from the selector: with it there, Space would open its list
        # instead of starting the flow.
        self.focus_set()

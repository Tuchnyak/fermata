"""The categories screen: the list of active categories and the form that adds one."""

import tkinter
from tkinter import colorchooser

import ttkbootstrap as ttk
from timer.i18n import t
from timer.ui.categories_view_model import DEFAULT_COLOR, CategoriesViewModel

SWATCH_SIZE = 16


class CategoriesScreen(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: CategoriesViewModel):
        super().__init__(parent)
        self._view_model = view_model
        self._color = DEFAULT_COLOR
        self._background = ttk.Style().lookup("TFrame", "background")

        self._list = ttk.Frame(self)
        self._list.pack(fill="x", pady=(0, 16))
        self._build_form()
        self._refresh_list()

    def _build_form(self) -> None:
        form = ttk.Frame(self)
        form.pack(fill="x")

        ttk.Label(form, text=t("categories.name")).pack(side="left")

        self._name_variable = tkinter.StringVar()
        name_entry = ttk.Entry(form, textvariable=self._name_variable)
        name_entry.pack(side="left", padx=8)
        name_entry.bind("<Return>", lambda event: self._add())

        self._color_swatch = self._create_swatch(form, self._color)
        self._color_swatch.pack(side="left")
        # Buttons do not take focus: Space on a focused button would press it as well as
        # act as a hotkey.
        ttk.Button(
            form,
            text=t("categories.choose_color"),
            command=self._choose_color,
            takefocus=False,
        ).pack(side="left", padx=8)
        ttk.Button(
            form, text=t("categories.add"), command=self._add, takefocus=False
        ).pack(side="left")

        self._error = ttk.Label(self, bootstyle="danger")
        self._error.pack(fill="x", pady=(8, 0))

    def _create_swatch(self, parent: tkinter.Misc, color: str) -> tkinter.Canvas:
        swatch = tkinter.Canvas(
            parent,
            width=SWATCH_SIZE,
            height=SWATCH_SIZE,
            background=self._background,
            highlightthickness=0,
        )
        swatch.create_oval(1, 1, SWATCH_SIZE - 1, SWATCH_SIZE - 1, fill=color, outline="")
        return swatch

    def _refresh_list(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        for category in self._view_model.categories():
            row = ttk.Frame(self._list)
            row.pack(fill="x", pady=2)
            self._create_swatch(row, category.color).pack(side="left")
            ttk.Label(row, text=category.name).pack(side="left", padx=8)

    def _choose_color(self) -> None:
        _, chosen_color = colorchooser.askcolor(
            color=self._color, title=t("categories.color_dialog_title"), parent=self
        )
        if chosen_color is None:  # the dialog was cancelled
            return
        self._color = chosen_color
        self._color_swatch.delete("all")
        self._color_swatch.create_oval(
            1, 1, SWATCH_SIZE - 1, SWATCH_SIZE - 1, fill=self._color, outline=""
        )

    def _add(self) -> None:
        message = self._view_model.add(self._name_variable.get(), self._color)
        if message is not None:
            self._error.configure(text=message)
            return
        self._error.configure(text="")
        self._name_variable.set("")
        self._refresh_list()

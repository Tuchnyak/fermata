"""The categories screen: the list of active categories with their controls, and the form
that adds one."""

import tkinter
from functools import partial

import ttkbootstrap as ttk
from fermata.i18n import t
from fermata.ui.dialogs import ask_yes_no
from fermata.storage.categories import Category
from fermata.ui.categories_view_model import DEFAULT_COLOR, CategoriesViewModel
from ttkbootstrap.dialogs import Querybox
from ttkbootstrap.dialogs.colorchooser import ColorChooserDialog

SWATCH_SIZE = 16


class _ColorChooserDialog(ColorChooserDialog):
    """The library's color chooser without its screen color dropper."""

    def create_buttonbox(self, master: tkinter.Misc) -> None:
        super().create_buttonbox(master)
        # The dropper is the only label of the button box the library builds.
        button_box = master.winfo_children()[-1]
        for child in button_box.winfo_children():
            if isinstance(child, ttk.Label):
                child.destroy()


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
        self._create_button(
            form, t("categories.choose_color"), self._choose_color
        ).pack(side="left", padx=8)
        self._create_button(form, t("categories.add"), self._add).pack(side="left")

        self._error = ttk.Label(self, bootstyle="danger")
        self._error.pack(fill="x", pady=(8, 0))

    def _create_button(self, parent, text, command, disabled=False) -> ttk.Button:
        # Buttons do not take focus: Space on a focused button would press it as well as
        # act as a hotkey.
        return ttk.Button(
            parent,
            text=text,
            command=command,
            takefocus=False,
            state="disabled" if disabled else "normal",
        )

    def _create_swatch(self, parent: tkinter.Misc, color: str) -> tkinter.Canvas:
        swatch = tkinter.Canvas(
            parent,
            width=SWATCH_SIZE,
            height=SWATCH_SIZE,
            background=self._background,
            highlightthickness=0,
        )
        self._paint_swatch(swatch, color)
        return swatch

    def _paint_swatch(self, swatch: tkinter.Canvas, color: str) -> None:
        swatch.delete("all")
        swatch.create_oval(1, 1, SWATCH_SIZE - 1, SWATCH_SIZE - 1, fill=color, outline="")

    def _refresh_list(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        for category in self._view_model.categories():
            self._build_row(category)

    def _build_row(self, category: Category) -> None:
        row = ttk.Frame(self._list)
        row.pack(fill="x", pady=2)
        self._create_swatch(row, category.color).pack(side="left")
        ttk.Label(row, text=category.name).pack(side="left", padx=8, fill="x", expand=True)

        # The system category cannot be changed, so its controls are disabled.
        controls = (
            (t("categories.rename"), self._rename),
            (t("categories.recolor"), self._recolor),
            (t("categories.archive"), self._archive),
        )
        for text, command in controls:
            self._create_button(
                row, text, partial(command, category), disabled=category.is_system
            ).pack(side="left", padx=(8, 0))

    def _choose_color(self) -> None:
        chosen_color = self._ask_color(self._color)
        if chosen_color is None:
            return
        self._color = chosen_color
        self._paint_swatch(self._color_swatch, self._color)

    def _ask_color(self, current_color: str) -> str | None:
        dialog = _ColorChooserDialog(
            parent=self,
            title=t("categories.color_dialog_title"),
            initialcolor=current_color,
        )
        dialog.show()
        choice = dialog.result  # None when the dialog was cancelled
        return None if choice is None else choice.hex.lower()

    def _add(self) -> None:
        message = self._view_model.add(self._name_variable.get(), self._color)
        if self._show_result(message):
            self._name_variable.set("")

    def _rename(self, category: Category) -> None:
        new_name = Querybox.get_string(
            prompt=t("categories.rename_prompt"),
            title=t("categories.rename_title"),
            initialvalue=category.name,
            parent=self,
        )
        if new_name is not None:
            self._show_result(self._view_model.rename(category.id, new_name))

    def _recolor(self, category: Category) -> None:
        new_color = self._ask_color(category.color)
        if new_color is not None:
            self._show_result(self._view_model.recolor(category.id, new_color))

    def _archive(self, category: Category) -> None:
        message = t("categories.archive_confirm", name=category.name)
        if ask_yes_no(self, message, t("categories.archive")):
            self._show_result(self._view_model.archive(category.id))

    def _show_result(self, message: str | None) -> bool:
        """Show the message of a rejected change, or refresh the list after a change.

        Return True if the change was made.
        """
        if message is not None:
            self._error.configure(text=message)
            return False
        self._error.configure(text="")
        self._refresh_list()
        return True

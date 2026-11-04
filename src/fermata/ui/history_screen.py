"""The history screen: a day or a week of finished work intervals, and what they add up to."""

import tkinter
from tkinter import font as tk_font

import ttkbootstrap as ttk
from PIL import ImageTk
from fermata.i18n import t
from fermata.ui.circle_image import render_circle
from fermata.ui.history_period import PeriodKind
from fermata.ui.history_view_model import HistoryView, HistoryViewModel

ROW_PADDING = 8  # added to the height of a text line to make the height of a list row
DOT_SHARE = 0.7  # the circle of a category is this part of a text line
TITLE_WIDTH = 24  # in characters: fits the longest title, two years in a week
TREE_STYLE = "History.Treeview"


class HistoryScreen(ttk.Frame):
    def __init__(self, parent: tkinter.Misc, view_model: HistoryViewModel):
        super().__init__(parent)
        self._view_model = view_model
        line = tk_font.nametofont("TkDefaultFont").metrics("linespace")
        self._dot_size = round(line * DOT_SHARE)
        ttk.Style().configure(TREE_STYLE, rowheight=line + ROW_PADDING)
        self._dots: dict[str, ImageTk.PhotoImage] = {}  # Tk draws only the pictures it holds
        self._show()

    def _show(self) -> None:
        """Draw the period again, from its start."""
        for child in self.winfo_children():
            child.destroy()
        view = self._view_model.view()
        self._build_controls(view)
        if view.rows:
            self._build_totals(view)  # packed at the bottom first, so the list gets the rest
            self._build_list(view)
        else:
            ttk.Label(self, text=t("history.empty")).pack(pady=32)

    def _build_controls(self, view: HistoryView) -> None:
        kinds = ttk.Frame(self)
        kinds.pack(fill="x")
        for kind, text, command in (
            (PeriodKind.DAY, t("history.day"), self._show_day),
            (PeriodKind.WEEK, t("history.week"), self._show_week),
        ):
            style = "primary" if view.kind == kind else "primary-outline"
            self._button(kinds, text, command, style).pack(side="left", padx=(0, 8))

        period = ttk.Frame(self)
        period.pack(fill="x", pady=8)
        self._button(period, t("history.previous"), self._previous).pack(side="left")
        # A title of a fixed width keeps the arrows where they are whatever the period is.
        ttk.Label(
            period, text=view.title, font=("TkDefaultFont", 14), width=TITLE_WIDTH, anchor="center"
        ).pack(side="left", padx=8)
        self._button(period, t("history.next"), self._next).pack(side="left")
        self._button(period, t("history.today"), self._go_to_today).pack(side="right")

    def _button(self, parent, text, command, style="secondary") -> ttk.Button:
        # Buttons do not take focus: Space on a focused button would press it as well as
        # act as a hotkey.
        return ttk.Button(
            parent, text=text, command=command, bootstyle=style, takefocus=False
        )

    def _build_list(self, view: HistoryView) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            frame,
            style=TREE_STYLE,
            columns=("started", "duration", "status"),
            selectmode="none",  # a list to read, nothing is chosen in it
            takefocus=False,
        )
        tree.heading("#0", text=t("history.column.category"), anchor="w")
        tree.heading("started", text=t("history.column.started"), anchor="w")
        tree.heading("duration", text=t("history.column.duration"), anchor="e")
        tree.heading("status", text=t("history.column.status"), anchor="w")
        tree.column("#0", stretch=True, minwidth=160)
        tree.column("started", width=110, stretch=False)
        tree.column("duration", width=125, stretch=False, anchor="e")
        tree.column("status", width=110, stretch=False)
        for row in view.rows:
            tree.insert(
                "",
                "end",
                text=" " + row.category,
                image=self._dot(row.color),
                values=(row.started, row.duration, row.status),
            )
        scroll_bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_bar.set)
        scroll_bar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

    def _build_totals(self, view: HistoryView) -> None:
        totals = ttk.Frame(self)
        totals.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Separator(totals).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        totals.columnconfigure(0, weight=1)
        grid_row = 1
        for category_total in view.totals:
            ttk.Label(
                totals,
                text=" " + category_total.category,
                image=self._dot(category_total.color),
                compound="left",
            ).grid(row=grid_row, column=0, sticky="w")
            ttk.Label(totals, text=category_total.duration).grid(
                row=grid_row, column=1, sticky="e"
            )
            grid_row += 1
        bold = ("TkDefaultFont", 10, "bold")
        ttk.Label(totals, text=t("history.total"), font=bold).grid(
            row=grid_row, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(totals, text=view.total, font=bold).grid(
            row=grid_row, column=1, sticky="e", pady=(4, 0)
        )

    def _dot(self, color: str) -> ImageTk.PhotoImage:
        """The smooth circle of a category, drawn once for each color."""
        if color not in self._dots:
            image = render_circle(self._dot_size, 1, color, color)
            self._dots[color] = ImageTk.PhotoImage(image)
        return self._dots[color]

    def _show_day(self) -> None:
        self._view_model.show_day()
        self._show()

    def _show_week(self) -> None:
        self._view_model.show_week()
        self._show()

    def _previous(self) -> None:
        self._view_model.previous()
        self._show()

    def _next(self) -> None:
        self._view_model.next()
        self._show()

    def _go_to_today(self) -> None:
        self._view_model.go_to_today()
        self._show()

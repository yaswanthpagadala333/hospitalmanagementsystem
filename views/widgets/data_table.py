"""
data_table.py
=============
CustomTkinter doesn't ship a table/grid widget, so this wraps
``tkinter.ttk.Treeview`` (the standard, well-tested option for tabular
data in Tk) with styling that matches the CustomTkinter theme, plus
convenience methods for loading rows, reading the current selection, and
handling double-click / selection callbacks. Every CRUD screen in the
app (patients, doctors, appointments, medicines, billing) reuses this
single component instead of re-implementing a table each time.
"""

from __future__ import annotations

from tkinter import ttk
from typing import Callable, Sequence

import customtkinter as ctk


class DataTable(ctk.CTkFrame):

    def __init__(
        self,
        master,
        columns: Sequence[str],
        column_widths: Sequence[int] | None = None,
        on_select: Callable[[dict], None] | None = None,
        on_double_click: Callable[[dict], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.columns = list(columns)
        self._on_select = on_select
        self._on_double_click = on_double_click
        self._row_data: dict[str, dict] = {}   # iid -> full record dict

        self._apply_treeview_style()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            container, columns=self.columns, show="headings",
            style="HMS.Treeview", selectmode="browse",
        )
        for i, col in enumerate(self.columns):
            width = column_widths[i] if column_widths and i < len(column_widths) else 120
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        self.tree.bind("<Double-1>", self._handle_double_click)

        self._sort_state: dict[str, bool] = {}

    # ------------------------------------------------------------------
    @staticmethod
    def _apply_treeview_style() -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2B2B2B" if is_dark else "#FFFFFF"
        fg = "#E5E5E5" if is_dark else "#1A1A1A"
        heading_bg = "#1F4E79"
        selected_bg = "#2E86C1"

        style.configure("HMS.Treeview", background=bg, foreground=fg, fieldbackground=bg,
                         rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        style.configure("HMS.Treeview.Heading", background=heading_bg, foreground="white",
                         font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("HMS.Treeview", background=[("selected", selected_bg)],
                   foreground=[("selected", "white")])
        style.map("HMS.Treeview.Heading", background=[("active", heading_bg)])

    # ------------------------------------------------------------------
    def load_rows(self, records: list[dict]) -> None:
        """Replace all rows. Each dict's keys must match ``self.columns``
        (case-insensitive lookup) plus it may carry an ``id`` used for
        the returned callback payload."""
        self.clear()
        for record in records:
            iid = str(record.get("id", id(record)))
            values = [record.get(col, record.get(col.lower().replace(" ", "_"), "")) for col in self.columns]
            self.tree.insert("", "end", iid=iid, values=values)
            self._row_data[iid] = record

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._row_data.clear()

    def get_selected(self) -> dict | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._row_data.get(selection[0])

    def _handle_select(self, _event) -> None:
        if self._on_select:
            record = self.get_selected()
            if record is not None:
                self._on_select(record)

    def _handle_double_click(self, _event) -> None:
        if self._on_double_click:
            record = self.get_selected()
            if record is not None:
                self._on_double_click(record)

    def _sort_by(self, column: str) -> None:
        reverse = self._sort_state.get(column, False)
        items = [(self.tree.set(k, column), k) for k in self.tree.get_children("")]

        def _sort_key(pair):
            value = pair[0]
            try:
                return float(str(value).replace(",", "").replace("$", ""))
            except ValueError:
                return str(value).lower()

        items.sort(key=_sort_key, reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
        self._sort_state[column] = not reverse

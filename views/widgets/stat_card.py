"""
stat_card.py
============
A small reusable "KPI card" widget (icon-free, colour-accented) used
across the dashboard and analytics screens to show a single number with
a label, e.g. "Total Patients: 128".
"""

from __future__ import annotations

import customtkinter as ctk


class StatCard(ctk.CTkFrame):
    """A rounded card displaying a title, a large value, and an optional
    subtitle/delta line. Call ``update_value()`` to refresh it in place."""

    def __init__(self, master, title: str, value: str, accent_color: str = "#2E86C1",
                 subtitle: str | None = None, icon: str | None = None, **kwargs) -> None:
        super().__init__(master, corner_radius=14, fg_color=("white", "gray17"),
                          border_width=1, border_color=("gray88", "gray24"), **kwargs)
        self._accent_color = accent_color

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(14, 0))

        if icon:
            icon_badge = ctk.CTkFrame(top_row, width=36, height=36, corner_radius=10, fg_color=accent_color)
            icon_badge.pack(side="left")
            icon_badge.pack_propagate(False)
            ctk.CTkLabel(icon_badge, text=icon, font=ctk.CTkFont(size=16)).place(relx=0.5, rely=0.5, anchor="center")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="top", fill="both", expand=True, padx=16, pady=(8, 14))

        self._title_label = ctk.CTkLabel(
            body, text=title, font=ctk.CTkFont(size=13, weight="normal"),
            text_color=("gray30", "gray70"), anchor="w",
        )
        self._title_label.pack(fill="x")

        self._value_label = ctk.CTkLabel(
            body, text=value, font=ctk.CTkFont(size=26, weight="bold"), anchor="w",
        )
        self._value_label.pack(fill="x", pady=(2, 0))

        self._subtitle_label = ctk.CTkLabel(
            body, text=subtitle or "", font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"), anchor="w",
        )
        if subtitle:
            self._subtitle_label.pack(fill="x")

    def update_value(self, value: str, subtitle: str | None = None) -> None:
        self._value_label.configure(text=value)
        if subtitle is not None:
            self._subtitle_label.configure(text=subtitle)
            if not self._subtitle_label.winfo_ismapped():
                self._subtitle_label.pack(fill="x")

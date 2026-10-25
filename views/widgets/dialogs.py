"""
dialogs.py
==========
Small, reusable modal helpers shared by every CRUD screen:

* ``show_info`` / ``show_error`` / ``confirm`` — thin wrappers around
  ``tkinter.messagebox`` so the rest of the codebase never imports
  ``tkinter`` directly.
* ``FormDialog`` — a generic "add / edit record" modal driven by a list
  of ``FieldSpec`` objects. Every CRUD screen (patients, doctors,
  medicines, ...) reuses this instead of hand-building a form each time,
  which keeps ~6 screens consistent and dramatically smaller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from tkinter import messagebox
from typing import Any, Callable, Sequence

import customtkinter as ctk

from utils.validators import ValidationError


def show_info(title: str, message: str) -> None:
    messagebox.showinfo(title, message)


def show_error(title: str, message: str) -> None:
    messagebox.showerror(title, message)


def confirm(title: str, message: str) -> bool:
    return messagebox.askyesno(title, message)


@dataclass
class FieldSpec:
    key: str
    label: str
    kind: str = "entry"              # entry | dropdown | textarea | password
    options: Sequence[str] = field(default_factory=tuple)
    initial: str = ""
    required: bool = True
    width: int = 320


class FormDialog(ctk.CTkToplevel):
    """
    A modal form built from ``FieldSpec`` definitions.

    ``on_submit`` receives a ``dict`` of ``{field_key: value}``. If it
    raises ``ValidationError`` (or any ``ValueError``), the message is
    shown inline and the dialog stays open so the user can correct the
    input instead of losing everything they typed.
    """

    def __init__(self, master, title: str, fields: Sequence[FieldSpec],
                 on_submit: Callable[[dict], None], submit_label: str = "Save") -> None:
        super().__init__(master)
        self.title(title)
        # Cap the dialog height so it always fits on screen; the field list
        # scrolls internally rather than growing the window unboundedly.
        content_height = min(120 + 54 * len(fields), 640)
        self.geometry(f"460x{content_height}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._fields = fields
        self._on_submit = on_submit
        self._widgets: dict[str, Any] = {}

        self._build_ui(title)

    def _build_ui(self, title: str) -> None:
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=17, weight="bold")).pack(pady=(18, 10), padx=20, anchor="w")

        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        for spec in self._fields:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=5)
            label_text = spec.label + (" *" if spec.required else "")
            ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(side="left")

            if spec.kind == "dropdown":
                var = ctk.StringVar(value=spec.initial or (spec.options[0] if spec.options else ""))
                widget = ctk.CTkOptionMenu(row, values=list(spec.options) or [""], variable=var, width=spec.width - 140)
                widget.pack(side="left", fill="x", expand=True)
                self._widgets[spec.key] = var
            elif spec.kind == "textarea":
                widget = ctk.CTkTextbox(row, height=60, width=spec.width - 140)
                if spec.initial:
                    widget.insert("1.0", spec.initial)
                widget.pack(side="left", fill="x", expand=True)
                self._widgets[spec.key] = widget
            else:
                show_char = "•" if spec.kind == "password" else ""
                widget = ctk.CTkEntry(row, width=spec.width - 140, show=show_char)
                if spec.initial:
                    widget.insert(0, spec.initial)
                widget.pack(side="left", fill="x", expand=True)
                self._widgets[spec.key] = widget

        self.error_label = ctk.CTkLabel(self, text="", text_color="#E74C3C", font=ctk.CTkFont(size=12))
        self.error_label.pack(pady=(6, 0))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(pady=16)
        ctk.CTkButton(button_row, text="Cancel", width=110, fg_color="gray50",
                      hover_color="gray40", command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(button_row, text="Save", width=110, command=self._handle_submit).pack(side="left", padx=6)

    def get_values(self) -> dict:
        values: dict[str, str] = {}
        for spec in self._fields:
            widget = self._widgets[spec.key]
            if isinstance(widget, ctk.StringVar):
                values[spec.key] = widget.get().strip()
            elif isinstance(widget, ctk.CTkTextbox):
                values[spec.key] = widget.get("1.0", "end").strip()
            else:
                values[spec.key] = widget.get().strip()
        return values

    def _handle_submit(self) -> None:
        values = self.get_values()
        for spec in self._fields:
            if spec.required and not values.get(spec.key):
                self.error_label.configure(text=f"'{spec.label}' is required.")
                return
        try:
            self._on_submit(values)
        except (ValidationError, ValueError) as exc:
            self.error_label.configure(text=str(exc))
            return
        self.destroy()

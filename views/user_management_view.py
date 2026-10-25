"""
user_management_view.py
========================
Admin-only screen for managing staff/login accounts. This is what lets
an administrator create *additional* administrator accounts (e.g.
``admin2``, ``admin3``) or accounts for doctors, receptionists and
pharmacists, instead of the app being permanently limited to the single
``admin`` account created on first run.

Mirrors the CRUD pattern used by ``doctor_view.py`` / ``patient_view.py``
(``DataTable`` + ``FormDialog``) so it looks and behaves consistently
with the rest of the application.
"""

from __future__ import annotations

import customtkinter as ctk

from config import config
from controllers.user_controller import UserController
from models.user import User
from utils.exporter import export_to_csv, export_to_json
from utils.validators import ValidationError
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, confirm, show_error, show_info

_COLUMNS = ["Username", "Full Name", "Role", "Email", "Status", "Last Login"]
_COLUMN_WIDTHS = [130, 190, 120, 200, 90, 150]


def _user_to_row(u: User) -> dict:
    return {
        "id": u.id,
        "Username": u.username,
        "Full Name": u.full_name,
        "Role": u.role,
        "Email": u.email or "—",
        "Status": "Active" if u.is_active else "Deactivated",
        "Last Login": u.last_login or "Never",
    }


class UserManagementView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 4))
        ctk.CTkLabel(header, text="Users & Access", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        ctk.CTkLabel(
            self, text="Create login accounts for admins, doctors, receptionists and pharmacists, "
                       "and control who can sign in.",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray65"),
        ).pack(fill="x", padx=24, pady=(0, 12), anchor="w")

        button_bar = ctk.CTkFrame(self, fg_color="transparent")
        button_bar.pack(fill="x", padx=24)
        ctk.CTkButton(
            button_bar, text="+ New User", command=self._open_add_dialog, width=140,
            fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_PRIMARY_HOVER,
        ).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Edit Role / Profile", command=self._open_edit_dialog, width=150,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Reset Password", command=self._open_password_dialog, width=140,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Activate / Deactivate", command=self._toggle_active_selected, width=170,
                      fg_color=config.COLOR_DANGER, hover_color=config.COLOR_DANGER_HOVER).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Export CSV", command=lambda: self._export("csv"), width=100,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", padx=24, pady=(12, 10))
        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Search by username, name or role...", width=420)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DataTable(
            table_frame, columns=_COLUMNS, column_widths=_COLUMN_WIDTHS,
            on_double_click=lambda _r: self._open_edit_dialog(),
        )
        self.table.pack(fill="both", expand=True)

    def on_show(self) -> None:
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        term = self.search_entry.get().strip().lower()
        users = UserController.list_all()
        if term:
            users = [
                u for u in users
                if term in u.username.lower() or term in u.full_name.lower() or term in u.role.lower()
            ]
        self.table.load_rows([_user_to_row(u) for u in users])

    def _selected_user(self) -> User | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select a user first.")
            return None
        return UserController.get_by_id(record["id"])

    # ------------------------------------------------------------------
    def _open_add_dialog(self) -> None:
        fields = [
            FieldSpec("username", "Username"),
            FieldSpec("full_name", "Full Name"),
            FieldSpec("role", "Role", kind="dropdown", options=config.ALL_ROLES, initial="Admin"),
            FieldSpec("email", "Email", required=False),
            FieldSpec("password", "Temporary Password", kind="password"),
        ]

        def on_submit(values: dict) -> None:
            new_user = User(
                username=values["username"], full_name=values["full_name"],
                role=values["role"], email=values.get("email") or None,
            )
            try:
                UserController.create_user(new_user, values["password"])
            except ValidationError as exc:
                raise ValueError(str(exc))
            self.refresh()
            show_info(
                "User Created",
                f"{new_user.full_name} can now sign in as '{new_user.username}' with the {new_user.role} role.",
            )

        FormDialog(self, "Add New User", fields, on_submit)

    def _open_edit_dialog(self) -> None:
        target = self._selected_user()
        if not target:
            return
        fields = [
            FieldSpec("full_name", "Full Name", initial=target.full_name),
            FieldSpec("role", "Role", kind="dropdown", options=config.ALL_ROLES, initial=target.role),
            FieldSpec("email", "Email", required=False, initial=target.email or ""),
        ]

        def on_submit(values: dict) -> None:
            if target.id == self.user.id and values["role"] != "Admin" and self.user.role == "Admin":
                raise ValueError("You can't remove your own Admin role while signed in.")
            target.full_name = values["full_name"]
            target.role = values["role"]
            target.email = values.get("email") or None
            try:
                UserController.update(target)
            except ValidationError as exc:
                raise ValueError(str(exc))
            self.refresh()
            show_info("User Updated", f"{target.full_name}'s account was updated.")

        FormDialog(self, f"Edit User — {target.username}", fields, on_submit)

    def _open_password_dialog(self) -> None:
        target = self._selected_user()
        if not target:
            return
        fields = [FieldSpec("password", "New Password", kind="password")]

        def on_submit(values: dict) -> None:
            try:
                UserController.change_password(target.id, values["password"])
            except ValidationError as exc:
                raise ValueError(str(exc))
            show_info("Password Reset", f"{target.username}'s password has been updated.")

        FormDialog(self, f"Reset Password — {target.username}", fields, on_submit, submit_label="Update")

    def _toggle_active_selected(self) -> None:
        target = self._selected_user()
        if not target:
            return
        if target.id == self.user.id:
            show_error("Not allowed", "You can't deactivate the account you're currently signed in with.")
            return

        if target.is_active:
            if confirm("Deactivate User", f"Deactivate '{target.username}'? They won't be able to sign in."):
                try:
                    UserController.deactivate(target.id)
                except ValidationError as exc:
                    show_error("Cannot Deactivate", str(exc))
                    return
        else:
            if confirm("Activate User", f"Re-activate '{target.username}'? They will be able to sign in again."):
                UserController.reactivate(target.id)
        self.refresh()

    def _export(self, fmt: str) -> None:
        users = UserController.list_all()
        if not users:
            show_error("Nothing to export", "There are no user accounts yet.")
            return
        rows = [u.to_dict() for u in users]
        try:
            path = export_to_csv(rows, "users") if fmt == "csv" else export_to_json(rows, "users")
        except Exception as exc:
            show_error("Export Failed", str(exc))
            return
        show_info("Export Complete", f"Exported {len(rows)} users to:\n{path}")

"""
patient_view.py
================
Full CRUD screen for patient records: searchable table, add/edit modal
forms (built on the shared ``FormDialog``), soft-delete (deactivate),
and CSV/JSON export.
"""

from __future__ import annotations

import customtkinter as ctk

from controllers.patient_controller import PatientController
from models.patient import Patient
from models.user import User
from utils.exporter import export_to_csv, export_to_json
from utils.logger import get_logger
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, confirm, show_error, show_info

logger = get_logger(__name__)

_COLUMNS = ["Code", "Name", "Age", "Gender", "Phone", "Blood Group", "Email"]
_COLUMN_WIDTHS = [90, 170, 50, 80, 130, 90, 200]


def _patient_to_row(p: Patient) -> dict:
    return {
        "id": p.id, "Code": p.patient_code, "Name": p.full_name, "Age": p.age,
        "Gender": p.gender, "Phone": p.phone, "Blood Group": p.blood_group or "—",
        "Email": p.email or "—",
    }


class PatientView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._selected_id: int | None = None
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Patients", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        button_bar = ctk.CTkFrame(header, fg_color="transparent")
        button_bar.pack(side="right")
        ctk.CTkButton(button_bar, text="+ New Patient", command=self._open_add_dialog, width=130).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Edit", command=self._open_edit_dialog, width=90,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Deactivate", command=self._deactivate_selected, width=100,
                      fg_color="#C0392B", hover_color="#922B21").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Export CSV", command=lambda: self._export("csv"), width=100,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Export JSON", command=lambda: self._export("json"), width=105,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", padx=24, pady=(0, 10))
        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Search by name, code, phone or email...", width=380)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DataTable(
            table_frame, columns=_COLUMNS, column_widths=_COLUMN_WIDTHS,
            on_select=self._handle_row_selected, on_double_click=lambda _r: self._open_edit_dialog(),
        )
        self.table.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        term = self.search_entry.get().strip()
        patients = PatientController.search(term) if term else PatientController.list_all()
        self.table.load_rows([_patient_to_row(p) for p in patients])

    def _handle_row_selected(self, record: dict) -> None:
        self._selected_id = record.get("id")

    def _selected_patient(self) -> Patient | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select a patient first.")
            return None
        return PatientController.get_by_id(record["id"])

    # ------------------------------------------------------------------
    def _open_add_dialog(self) -> None:
        fields = [
            FieldSpec("first_name", "First Name"),
            FieldSpec("last_name", "Last Name"),
            FieldSpec("date_of_birth", "Date of Birth (YYYY-MM-DD)"),
            FieldSpec("gender", "Gender", kind="dropdown", options=("Male", "Female", "Other")),
            FieldSpec("phone", "Phone"),
            FieldSpec("email", "Email", required=False),
            FieldSpec("blood_group", "Blood Group", kind="dropdown",
                      options=("", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"), required=False),
            FieldSpec("address", "Address", required=False),
            FieldSpec("emergency_contact_name", "Emergency Contact Name", required=False),
            FieldSpec("emergency_contact_phone", "Emergency Contact Phone", required=False),
            FieldSpec("allergies", "Known Allergies", kind="textarea", required=False),
        ]

        def on_submit(values: dict) -> None:
            patient = Patient(
                first_name=values["first_name"], last_name=values["last_name"],
                date_of_birth=values["date_of_birth"], gender=values["gender"], phone=values["phone"],
                email=values.get("email") or None, blood_group=values.get("blood_group") or None,
                address=values.get("address") or None,
                emergency_contact_name=values.get("emergency_contact_name") or None,
                emergency_contact_phone=values.get("emergency_contact_phone") or None,
                allergies=values.get("allergies") or None,
            )
            PatientController.create(patient)
            self.refresh()
            show_info("Patient Added", f"{patient.full_name} was registered as {patient.patient_code}.")

        FormDialog(self, "Register New Patient", fields, on_submit)

    def _open_edit_dialog(self) -> None:
        patient = self._selected_patient()
        if not patient:
            return

        fields = [
            FieldSpec("first_name", "First Name", initial=patient.first_name),
            FieldSpec("last_name", "Last Name", initial=patient.last_name),
            FieldSpec("date_of_birth", "Date of Birth (YYYY-MM-DD)", initial=patient.date_of_birth),
            FieldSpec("gender", "Gender", kind="dropdown", options=("Male", "Female", "Other"), initial=patient.gender),
            FieldSpec("phone", "Phone", initial=patient.phone),
            FieldSpec("email", "Email", required=False, initial=patient.email or ""),
            FieldSpec("blood_group", "Blood Group", kind="dropdown",
                      options=("", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"),
                      required=False, initial=patient.blood_group or ""),
            FieldSpec("address", "Address", required=False, initial=patient.address or ""),
            FieldSpec("emergency_contact_name", "Emergency Contact Name", required=False,
                      initial=patient.emergency_contact_name or ""),
            FieldSpec("emergency_contact_phone", "Emergency Contact Phone", required=False,
                      initial=patient.emergency_contact_phone or ""),
            FieldSpec("allergies", "Known Allergies", kind="textarea", required=False, initial=patient.allergies or ""),
        ]

        def on_submit(values: dict) -> None:
            patient.first_name = values["first_name"]
            patient.last_name = values["last_name"]
            patient.date_of_birth = values["date_of_birth"]
            patient.gender = values["gender"]
            patient.phone = values["phone"]
            patient.email = values.get("email") or None
            patient.blood_group = values.get("blood_group") or None
            patient.address = values.get("address") or None
            patient.emergency_contact_name = values.get("emergency_contact_name") or None
            patient.emergency_contact_phone = values.get("emergency_contact_phone") or None
            patient.allergies = values.get("allergies") or None
            PatientController.update(patient)
            self.refresh()
            show_info("Patient Updated", f"{patient.full_name}'s record was updated.")

        FormDialog(self, f"Edit Patient — {patient.patient_code}", fields, on_submit)

    def _deactivate_selected(self) -> None:
        patient = self._selected_patient()
        if not patient:
            return
        if confirm("Deactivate Patient", f"Deactivate {patient.full_name} ({patient.patient_code})? "
                                          f"Their history is kept, but they'll be hidden from active lists."):
            PatientController.deactivate(patient.id)
            self.refresh()

    def _export(self, fmt: str) -> None:
        patients = PatientController.list_all(include_inactive=True)
        if not patients:
            show_error("Nothing to export", "There are no patient records yet.")
            return
        rows = [p.to_dict() for p in patients]
        try:
            path = export_to_csv(rows, "patients") if fmt == "csv" else export_to_json(rows, "patients")
        except Exception as exc:
            show_error("Export Failed", str(exc))
            return
        show_info("Export Complete", f"Exported {len(rows)} patients to:\n{path}")

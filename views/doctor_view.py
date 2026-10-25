"""
doctor_view.py
===============
Full CRUD screen for doctor/physician records — mirrors ``patient_view``
in structure for consistency, since both are simple resource screens
built on the shared ``DataTable`` and ``FormDialog`` components.
"""

from __future__ import annotations

import customtkinter as ctk

from controllers.doctor_controller import DoctorController
from models.doctor import Doctor
from models.user import User
from utils.exporter import export_to_csv, export_to_json
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, confirm, show_error, show_info

_COLUMNS = ["Code", "Name", "Specialization", "Department", "Phone", "Fee", "Experience"]
_COLUMN_WIDTHS = [90, 170, 150, 130, 130, 80, 90]


def _doctor_to_row(d: Doctor) -> dict:
    return {
        "id": d.id, "Code": d.doctor_code, "Name": d.full_name, "Specialization": d.specialization,
        "Department": d.department, "Phone": d.phone, "Fee": f"${d.consultation_fee:,.2f}",
        "Experience": f"{d.years_experience} yrs",
    }


class DoctorView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Doctors", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        button_bar = ctk.CTkFrame(header, fg_color="transparent")
        button_bar.pack(side="right")
        ctk.CTkButton(button_bar, text="+ New Doctor", command=self._open_add_dialog, width=130).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Edit", command=self._open_edit_dialog, width=90,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Deactivate", command=self._deactivate_selected, width=100,
                      fg_color="#C0392B", hover_color="#922B21").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Export CSV", command=lambda: self._export("csv"), width=100,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", padx=24, pady=(0, 10))
        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Search by name, code, specialization or department...", width=420)
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

    def refresh(self) -> None:
        term = self.search_entry.get().strip()
        doctors = DoctorController.search(term) if term else DoctorController.list_all()
        self.table.load_rows([_doctor_to_row(d) for d in doctors])

    def _selected_doctor(self) -> Doctor | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select a doctor first.")
            return None
        return DoctorController.get_by_id(record["id"])

    def _open_add_dialog(self) -> None:
        fields = [
            FieldSpec("first_name", "First Name"),
            FieldSpec("last_name", "Last Name"),
            FieldSpec("specialization", "Specialization"),
            FieldSpec("department", "Department"),
            FieldSpec("phone", "Phone"),
            FieldSpec("email", "Email", required=False),
            FieldSpec("license_number", "License No. (e.g. MED-12345)"),
            FieldSpec("consultation_fee", "Consultation Fee"),
            FieldSpec("years_experience", "Years of Experience", required=False, initial="0"),
        ]

        def on_submit(values: dict) -> None:
            try:
                fee = float(values["consultation_fee"])
                exp = int(values.get("years_experience") or 0)
            except ValueError:
                raise ValueError("Fee and experience must be numeric.")
            doctor = Doctor(
                first_name=values["first_name"], last_name=values["last_name"],
                specialization=values["specialization"], department=values["department"],
                phone=values["phone"], email=values.get("email") or None,
                license_number=values["license_number"].upper(), consultation_fee=fee, years_experience=exp,
            )
            DoctorController.create(doctor)
            self.refresh()
            show_info("Doctor Added", f"{doctor.full_name} was registered as {doctor.doctor_code}.")

        FormDialog(self, "Add New Doctor", fields, on_submit)

    def _open_edit_dialog(self) -> None:
        doctor = self._selected_doctor()
        if not doctor:
            return
        fields = [
            FieldSpec("first_name", "First Name", initial=doctor.first_name),
            FieldSpec("last_name", "Last Name", initial=doctor.last_name),
            FieldSpec("specialization", "Specialization", initial=doctor.specialization),
            FieldSpec("department", "Department", initial=doctor.department),
            FieldSpec("phone", "Phone", initial=doctor.phone),
            FieldSpec("email", "Email", required=False, initial=doctor.email or ""),
            FieldSpec("license_number", "License No.", initial=doctor.license_number),
            FieldSpec("consultation_fee", "Consultation Fee", initial=str(doctor.consultation_fee)),
            FieldSpec("years_experience", "Years of Experience", initial=str(doctor.years_experience)),
        ]

        def on_submit(values: dict) -> None:
            try:
                fee = float(values["consultation_fee"])
                exp = int(values.get("years_experience") or 0)
            except ValueError:
                raise ValueError("Fee and experience must be numeric.")
            doctor.first_name = values["first_name"]
            doctor.last_name = values["last_name"]
            doctor.specialization = values["specialization"]
            doctor.department = values["department"]
            doctor.phone = values["phone"]
            doctor.email = values.get("email") or None
            doctor.license_number = values["license_number"].upper()
            doctor.consultation_fee = fee
            doctor.years_experience = exp
            DoctorController.update(doctor)
            self.refresh()
            show_info("Doctor Updated", f"{doctor.full_name}'s record was updated.")

        FormDialog(self, f"Edit Doctor — {doctor.doctor_code}", fields, on_submit)

    def _deactivate_selected(self) -> None:
        doctor = self._selected_doctor()
        if not doctor:
            return
        if confirm("Deactivate Doctor", f"Deactivate {doctor.full_name}? They won't appear when booking new appointments."):
            DoctorController.deactivate(doctor.id)
            self.refresh()

    def _export(self, fmt: str) -> None:
        doctors = DoctorController.list_all(include_inactive=True)
        if not doctors:
            show_error("Nothing to export", "There are no doctor records yet.")
            return
        rows = [d.to_dict() for d in doctors]
        try:
            path = export_to_csv(rows, "doctors") if fmt == "csv" else export_to_json(rows, "doctors")
        except Exception as exc:
            show_error("Export Failed", str(exc))
            return
        show_info("Export Complete", f"Exported {len(rows)} doctors to:\n{path}")

"""
appointment_view.py
====================
Scheduling screen: date-filtered appointment list, a booking dialog that
validates against live conflict-checking in the controller, and inline
status actions (complete / cancel) plus a diagnosis/notes editor.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from controllers.appointment_controller import AppointmentController
from controllers.doctor_controller import DoctorController
from controllers.patient_controller import PatientController
from models.appointment import Appointment
from models.user import User
from utils.logger import get_logger
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, confirm, show_error, show_info

logger = get_logger(__name__)

_COLUMNS = ["Date", "Time", "Patient", "Doctor", "Status", "Reason"]
_COLUMN_WIDTHS = [100, 70, 160, 160, 100, 220]


def _appt_to_row(a: Appointment) -> dict:
    return {
        "id": a.id, "Date": a.appointment_date, "Time": a.appointment_time,
        "Patient": a.patient_name, "Doctor": a.doctor_name, "Status": a.status,
        "Reason": a.reason or "—",
    }


class AppointmentView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._filter_mode = "all"   # "all" | "today" | "date"
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Appointments", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        button_bar = ctk.CTkFrame(header, fg_color="transparent")
        button_bar.pack(side="right")
        ctk.CTkButton(button_bar, text="+ Book Appointment", command=self._open_booking_dialog, width=160).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Mark Completed", command=lambda: self._change_status("Completed"),
                      width=130, fg_color="#28B463", hover_color="#1E8449").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Cancel", command=lambda: self._change_status("Cancelled"),
                      width=90, fg_color="#C0392B", hover_color="#922B21").pack(side="right", padx=4)

        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkButton(filter_bar, text="All", width=70, command=lambda: self._set_filter("all")).pack(side="left", padx=(0, 6))
        ctk.CTkButton(filter_bar, text="Today", width=70, command=lambda: self._set_filter("today")).pack(side="left", padx=6)
        self.date_entry = ctk.CTkEntry(filter_bar, placeholder_text="YYYY-MM-DD", width=120)
        self.date_entry.pack(side="left", padx=6)
        ctk.CTkButton(filter_bar, text="Go", width=50, command=lambda: self._set_filter("date")).pack(side="left")

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DataTable(table_frame, columns=_COLUMNS, column_widths=_COLUMN_WIDTHS,
                               on_double_click=self._open_details_dialog)
        self.table.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def _set_filter(self, mode: str) -> None:
        self._filter_mode = mode
        self.refresh()

    def refresh(self) -> None:
        if self._filter_mode == "today":
            appts = AppointmentController.list_for_date(date.today().isoformat())
        elif self._filter_mode == "date" and self.date_entry.get().strip():
            appts = AppointmentController.list_for_date(self.date_entry.get().strip())
        else:
            appts = AppointmentController.list_all()
        self.table.load_rows([_appt_to_row(a) for a in appts])

    def _selected_appointment(self) -> Appointment | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select an appointment first.")
            return None
        return AppointmentController.get_by_id(record["id"])

    # ------------------------------------------------------------------
    def _open_booking_dialog(self) -> None:
        patients = PatientController.list_all()
        doctors = DoctorController.list_all()
        if not patients or not doctors:
            show_error("Cannot Book", "You need at least one active patient and one active doctor first.")
            return

        patient_lookup = {f"{p.full_name} ({p.patient_code})": p.id for p in patients}
        doctor_lookup = {f"{d.full_name} — {d.specialization}": d.id for d in doctors}

        fields = [
            FieldSpec("patient", "Patient", kind="dropdown", options=tuple(patient_lookup.keys())),
            FieldSpec("doctor", "Doctor", kind="dropdown", options=tuple(doctor_lookup.keys())),
            FieldSpec("appointment_date", "Date (YYYY-MM-DD)", initial=date.today().isoformat()),
            FieldSpec("appointment_time", "Time (HH:MM, 24h)", initial="09:00"),
            FieldSpec("reason", "Reason for Visit", required=False),
        ]

        def on_submit(values: dict) -> None:
            appt = Appointment(
                patient_id=patient_lookup[values["patient"]],
                doctor_id=doctor_lookup[values["doctor"]],
                appointment_date=values["appointment_date"],
                appointment_time=values["appointment_time"],
                reason=values.get("reason") or None,
            )
            AppointmentController.book(appt)
            self.refresh()
            show_info("Appointment Booked", f"Booked for {values['appointment_date']} at {values['appointment_time']}.")

        FormDialog(self, "Book New Appointment", fields, on_submit)

    def _open_details_dialog(self, _record: dict) -> None:
        appt = self._selected_appointment()
        if not appt:
            return
        fields = [
            FieldSpec("status", "Status", kind="dropdown",
                      options=("Scheduled", "Completed", "Cancelled", "No-Show"), initial=appt.status),
            FieldSpec("diagnosis", "Diagnosis", required=False, initial=appt.diagnosis or ""),
            FieldSpec("notes", "Notes", kind="textarea", required=False, initial=appt.notes or ""),
        ]

        def on_submit(values: dict) -> None:
            AppointmentController.update_status(
                appt.id, values["status"], diagnosis=values.get("diagnosis") or None, notes=values.get("notes") or None,
            )
            self.refresh()
            show_info("Appointment Updated", "The appointment record was updated.")

        FormDialog(self, f"Appointment — {appt.patient_name} with {appt.doctor_name}", fields, on_submit)

    def _change_status(self, status: str) -> None:
        appt = self._selected_appointment()
        if not appt:
            return
        if status == "Cancelled" and not confirm("Cancel Appointment", "Cancel this appointment?"):
            return
        AppointmentController.update_status(appt.id, status)
        self.refresh()

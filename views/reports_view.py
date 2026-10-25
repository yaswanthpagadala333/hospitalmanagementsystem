"""
reports_view.py
================
Central place to generate and export documents: patient medical
summaries (PDF, via ReportLab), plus bulk data exports (CSV/JSON) of
every major table — separate from the per-record "Print Invoice" action
that lives on the Billing screen.
"""

from __future__ import annotations

import os
import platform
import subprocess

import customtkinter as ctk

from controllers.appointment_controller import AppointmentController
from controllers.billing_controller import BillingController
from controllers.doctor_controller import DoctorController
from controllers.medicine_controller import MedicineController
from controllers.patient_controller import PatientController
from models.user import User
from reports.pdf_generator import generate_patient_summary_pdf
from utils.exporter import export_to_csv, export_to_json
from utils.logger import get_logger
from views.widgets.dialogs import FieldSpec, FormDialog, show_error, show_info

logger = get_logger(__name__)


def _open_file(path) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        logger.info("Could not auto-open file (%s); it was still saved to disk.", exc)


class ReportsView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text="Reports & Exports", font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w", padx=24, pady=(20, 16))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self._build_section(
            scroll, "Patient Medical Summary (PDF)",
            "Generates a full demographic + appointment-history report for one patient.",
            "Generate...", self._open_patient_summary_dialog,
        )

        self._build_data_export_section(scroll)

    def _build_section(self, parent, title: str, description: str, button_text: str, command) -> None:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=("gray95", "gray17"))
        card.pack(fill="x", pady=8)
        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=18, pady=14)
        ctk.CTkLabel(text_frame, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(text_frame, text=description, font=ctk.CTkFont(size=12),
                     text_color=("gray40", "gray60"), wraplength=560, justify="left").pack(anchor="w")
        ctk.CTkButton(card, text=button_text, command=command, width=140).pack(side="right", padx=18)

    def _build_data_export_section(self, parent) -> None:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=("gray95", "gray17"))
        card.pack(fill="x", pady=8)
        ctk.CTkLabel(card, text="Bulk Data Export", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(card, text="Export full tables to CSV or JSON for backup, auditing, or use in other tools.",
                     font=ctk.CTkFont(size=12), text_color=("gray40", "gray60")).pack(anchor="w", padx=18, pady=(0, 10))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(0, 16))

        datasets = [
            ("Patients", lambda: [p.to_dict() for p in PatientController.list_all(include_inactive=True)]),
            ("Doctors", lambda: [d.to_dict() for d in DoctorController.list_all(include_inactive=True)]),
            ("Appointments", lambda: [a.to_dict() for a in AppointmentController.list_all()]),
            ("Medicines", lambda: [m.to_dict() for m in MedicineController.list_all()]),
            ("Bills", lambda: [b.to_dict() for b in BillingController.list_all()]),
        ]
        for i, (name, loader) in enumerate(datasets):
            row = ctk.CTkFrame(grid, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=3)
            grid.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=name, width=140, anchor="w").pack(side="left")
            ctk.CTkButton(row, text="CSV", width=70, fg_color="gray50", hover_color="gray40",
                          command=lambda n=name, f=loader: self._export_dataset(n, f, "csv")).pack(side="left", padx=4)
            ctk.CTkButton(row, text="JSON", width=70, fg_color="gray50", hover_color="gray40",
                          command=lambda n=name, f=loader: self._export_dataset(n, f, "json")).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def _export_dataset(self, name: str, loader, fmt: str) -> None:
        rows = loader()
        if not rows:
            show_error("Nothing to Export", f"There is no {name.lower()} data yet.")
            return
        try:
            path = export_to_csv(rows, name.lower()) if fmt == "csv" else export_to_json(rows, name.lower())
        except Exception as exc:
            show_error("Export Failed", str(exc))
            return
        show_info("Export Complete", f"Exported {len(rows)} {name.lower()} records to:\n{path}")

    def _open_patient_summary_dialog(self) -> None:
        patients = PatientController.list_all()
        if not patients:
            show_error("No Patients", "There are no patients registered yet.")
            return
        lookup = {f"{p.full_name} ({p.patient_code})": p.id for p in patients}
        fields = [FieldSpec("patient", "Patient", kind="dropdown", options=tuple(lookup.keys()))]

        def on_submit(values: dict) -> None:
            patient = PatientController.get_by_id(lookup[values["patient"]])
            appts = AppointmentController.list_for_patient(patient.id)
            try:
                path = generate_patient_summary_pdf(patient, appts)
            except Exception as exc:
                raise ValueError(f"Could not generate PDF: {exc}")
            show_info("Report Generated", f"Saved to:\n{path}")
            _open_file(path)

        FormDialog(self, "Generate Patient Summary", fields, on_submit, submit_label="Generate")

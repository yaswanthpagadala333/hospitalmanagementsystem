"""
appointment.py
==============
Domain model for a scheduled consultation between a patient and a doctor.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from utils import validators
from utils.validators import require

VALID_STATUSES = ("Scheduled", "Completed", "Cancelled", "No-Show")


@dataclass
class Appointment:
    patient_id: int
    doctor_id: int
    appointment_date: str      # YYYY-MM-DD
    appointment_time: str      # HH:MM (24h)
    status: str = "Scheduled"
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    # Populated by joined queries for display purposes only (not persisted).
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None

    def validate(self) -> None:
        require(isinstance(self.patient_id, int) and self.patient_id > 0, "A valid patient must be selected.")
        require(isinstance(self.doctor_id, int) and self.doctor_id > 0, "A valid doctor must be selected.")
        require(validators.is_valid_date(self.appointment_date), "Appointment date must be YYYY-MM-DD.")
        require(validators.is_valid_time(self.appointment_time), "Appointment time must be HH:MM (24h).")
        require(self.status in VALID_STATUSES, f"Status must be one of {VALID_STATUSES}.")

    @property
    def datetime_value(self) -> datetime:
        return datetime.strptime(f"{self.appointment_date} {self.appointment_time}", "%Y-%m-%d %H:%M")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Appointment":
        data = dict(row)
        patient_name = data.pop("patient_name", None)
        doctor_name = data.pop("doctor_name", None)
        known_fields = {
            "id", "patient_id", "doctor_id", "appointment_date", "appointment_time",
            "status", "reason", "diagnosis", "notes", "created_at",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}
        obj = cls(**filtered)
        obj.patient_name = patient_name
        obj.doctor_name = doctor_name
        return obj

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "status": self.status,
            "reason": self.reason,
            "diagnosis": self.diagnosis,
            "notes": self.notes,
            "created_at": self.created_at,
        }

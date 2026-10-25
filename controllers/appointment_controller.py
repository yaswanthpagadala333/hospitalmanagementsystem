"""
appointment_controller.py
==========================
Business logic for scheduling: conflict detection (a doctor cannot be
double-booked for the same date/time — also enforced at the DB level via
a UNIQUE constraint, but checked here first so the user gets a friendly
error instead of a raw SQLite exception), clinic-hours validation, and
status transitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from config import config
from database.database import db, DatabaseError
from models.appointment import Appointment
from utils.logger import get_logger
from utils.validators import require, ValidationError

logger = get_logger(__name__)

_SELECT_JOINED = """
    SELECT a.*,
           (p.first_name || ' ' || p.last_name) AS patient_name,
           (d.first_name || ' ' || d.last_name)  AS doctor_name
    FROM appointments a
    JOIN patients p ON p.id = a.patient_id
    JOIN doctors  d ON d.id = a.doctor_id
"""


class AppointmentController:

    @staticmethod
    def _check_clinic_hours(appointment_time: str) -> None:
        hour = int(appointment_time.split(":")[0])
        require(
            config.CLINIC_OPEN_HOUR <= hour < config.CLINIC_CLOSE_HOUR,
            f"Appointments must be between {config.CLINIC_OPEN_HOUR}:00 and {config.CLINIC_CLOSE_HOUR}:00.",
        )

    @staticmethod
    def _check_conflict(doctor_id: int, appointment_date: str, appointment_time: str,
                         exclude_id: Optional[int] = None) -> None:
        query = """
            SELECT id FROM appointments
            WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ?
              AND status != 'Cancelled'
        """
        params: list = [doctor_id, appointment_date, appointment_time]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        clash = db.fetch_one(query, tuple(params))
        require(clash is None, "This doctor already has an appointment at that date and time.")

    # ------------------------------------------------------------------
    @classmethod
    def book(cls, appointment: Appointment) -> Appointment:
        appointment.validate()
        cls._check_clinic_hours(appointment.appointment_time)
        cls._check_conflict(appointment.doctor_id, appointment.appointment_date, appointment.appointment_time)

        query = """
            INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, appointment_time, status, reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            appointment.patient_id, appointment.doctor_id, appointment.appointment_date,
            appointment.appointment_time, appointment.status, appointment.reason, appointment.notes,
        )
        try:
            cursor = db.execute(query, params)
        except DatabaseError as exc:
            raise ValidationError("This time slot was just taken. Please choose another.") from exc
        appointment.id = cursor.lastrowid
        logger.info("Booked appointment #%s: patient=%s doctor=%s at %s %s",
                    appointment.id, appointment.patient_id, appointment.doctor_id,
                    appointment.appointment_date, appointment.appointment_time)
        return appointment

    @classmethod
    def reschedule(cls, appointment_id: int, new_date: str, new_time: str) -> None:
        appt = cls.get_by_id(appointment_id)
        if not appt:
            raise ValueError("Appointment not found.")
        cls._check_clinic_hours(new_time)
        cls._check_conflict(appt.doctor_id, new_date, new_time, exclude_id=appointment_id)
        db.execute(
            "UPDATE appointments SET appointment_date = ?, appointment_time = ? WHERE id = ?",
            (new_date, new_time, appointment_id),
        )
        logger.info("Rescheduled appointment #%s to %s %s", appointment_id, new_date, new_time)

    @staticmethod
    def update_status(appointment_id: int, status: str, diagnosis: Optional[str] = None,
                       notes: Optional[str] = None) -> None:
        from models.appointment import VALID_STATUSES
        require(status in VALID_STATUSES, f"Status must be one of {VALID_STATUSES}.")
        db.execute(
            "UPDATE appointments SET status = ?, diagnosis = COALESCE(?, diagnosis), notes = COALESCE(?, notes) WHERE id = ?",
            (status, diagnosis, notes, appointment_id),
        )
        logger.info("Appointment #%s status -> %s", appointment_id, status)

    @staticmethod
    def cancel(appointment_id: int) -> None:
        db.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
        logger.info("Cancelled appointment #%s", appointment_id)

    @staticmethod
    def get_by_id(appointment_id: int) -> Optional[Appointment]:
        row = db.fetch_one(_SELECT_JOINED + " WHERE a.id = ?", (appointment_id,))
        return Appointment.from_row(row) if row else None

    @staticmethod
    def list_all() -> list[Appointment]:
        rows = db.fetch_all(_SELECT_JOINED + " ORDER BY a.appointment_date DESC, a.appointment_time DESC")
        return [Appointment.from_row(r) for r in rows]

    @staticmethod
    def list_for_date(date_str: str) -> list[Appointment]:
        rows = db.fetch_all(
            _SELECT_JOINED + " WHERE a.appointment_date = ? ORDER BY a.appointment_time",
            (date_str,),
        )
        return [Appointment.from_row(r) for r in rows]

    @staticmethod
    def list_for_patient(patient_id: int) -> list[Appointment]:
        rows = db.fetch_all(
            _SELECT_JOINED + " WHERE a.patient_id = ? ORDER BY a.appointment_date DESC",
            (patient_id,),
        )
        return [Appointment.from_row(r) for r in rows]

    @staticmethod
    def list_for_doctor(doctor_id: int, date_str: Optional[str] = None) -> list[Appointment]:
        query = _SELECT_JOINED + " WHERE a.doctor_id = ?"
        params: list = [doctor_id]
        if date_str:
            query += " AND a.appointment_date = ?"
            params.append(date_str)
        query += " ORDER BY a.appointment_date, a.appointment_time"
        rows = db.fetch_all(query, tuple(params))
        return [Appointment.from_row(r) for r in rows]

    @staticmethod
    def count_today() -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        row = db.fetch_one(
            "SELECT COUNT(*) AS c FROM appointments WHERE appointment_date = ? AND status != 'Cancelled'",
            (today,),
        )
        return row["c"] if row else 0

    @staticmethod
    def available_slots(doctor_id: int, date_str: str) -> list[str]:
        """Return free HH:MM slots for a doctor on a given date, based on
        clinic hours and the configured appointment slot length."""
        booked_rows = db.fetch_all(
            "SELECT appointment_time FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled'",
            (doctor_id, date_str),
        )
        booked = {r["appointment_time"] for r in booked_rows}

        slots = []
        minutes = config.APPOINTMENT_SLOT_MINUTES
        for hour in range(config.CLINIC_OPEN_HOUR, config.CLINIC_CLOSE_HOUR):
            for minute in range(0, 60, minutes):
                slot = f"{hour:02d}:{minute:02d}"
                if slot not in booked:
                    slots.append(slot)
        return slots

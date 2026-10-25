"""
patient_controller.py
======================
Business logic for patient management: CRUD operations, patient-code
generation, and search. Controllers are the only layer allowed to talk
to both the database and the models — views never touch SQL directly.
"""

from __future__ import annotations

from typing import Optional

from database.database import db
from models.patient import Patient
from utils.helpers import generate_code, now_iso
from utils.logger import get_logger
from utils.validators import sanitize_search_term

logger = get_logger(__name__)


class PatientController:

    @staticmethod
    def _next_patient_code() -> str:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM patients")
        return generate_code("PAT", (row["c"] if row else 0) + 1)

    # ------------------------------------------------------------------
    @classmethod
    def create(cls, patient: Patient) -> Patient:
        patient.validate()
        patient.patient_code = cls._next_patient_code()
        query = """
            INSERT INTO patients
                (patient_code, first_name, last_name, date_of_birth, gender, phone,
                 email, address, blood_group, emergency_contact_name,
                 emergency_contact_phone, allergies, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            patient.patient_code, patient.first_name, patient.last_name,
            patient.date_of_birth, patient.gender, patient.phone, patient.email,
            patient.address, patient.blood_group, patient.emergency_contact_name,
            patient.emergency_contact_phone, patient.allergies, int(patient.is_active),
        )
        cursor = db.execute(query, params)
        patient.id = cursor.lastrowid
        logger.info("Created patient #%s (%s)", patient.id, patient.patient_code)
        return patient

    @staticmethod
    def update(patient: Patient) -> None:
        if not patient.id:
            raise ValueError("Cannot update a patient without an id.")
        patient.validate()
        query = """
            UPDATE patients SET
                first_name=?, last_name=?, date_of_birth=?, gender=?, phone=?,
                email=?, address=?, blood_group=?, emergency_contact_name=?,
                emergency_contact_phone=?, allergies=?, is_active=?, updated_at=?
            WHERE id=?
        """
        params = (
            patient.first_name, patient.last_name, patient.date_of_birth, patient.gender,
            patient.phone, patient.email, patient.address, patient.blood_group,
            patient.emergency_contact_name, patient.emergency_contact_phone,
            patient.allergies, int(patient.is_active), now_iso(), patient.id,
        )
        db.execute(query, params)
        logger.info("Updated patient #%s", patient.id)

    @staticmethod
    def deactivate(patient_id: int) -> None:
        """Soft-delete: patients are never hard-deleted so appointment/billing
        history stays intact; they are simply marked inactive."""
        db.execute("UPDATE patients SET is_active = 0, updated_at = ? WHERE id = ?", (now_iso(), patient_id))
        logger.info("Deactivated patient #%s", patient_id)

    @staticmethod
    def reactivate(patient_id: int) -> None:
        db.execute("UPDATE patients SET is_active = 1, updated_at = ? WHERE id = ?", (now_iso(), patient_id))

    @staticmethod
    def get_by_id(patient_id: int) -> Optional[Patient]:
        row = db.fetch_one("SELECT * FROM patients WHERE id = ?", (patient_id,))
        return Patient.from_row(row) if row else None

    @staticmethod
    def list_all(include_inactive: bool = False) -> list[Patient]:
        query = "SELECT * FROM patients"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY last_name, first_name"
        rows = db.fetch_all(query)
        return [Patient.from_row(r) for r in rows]

    @staticmethod
    def search(term: str) -> list[Patient]:
        term = sanitize_search_term(term)
        like = f"%{term}%"
        query = """
            SELECT * FROM patients
            WHERE is_active = 1 AND (
                first_name LIKE ? OR last_name LIKE ? OR patient_code LIKE ?
                OR phone LIKE ? OR email LIKE ?
            )
            ORDER BY last_name, first_name
        """
        rows = db.fetch_all(query, (like, like, like, like, like))
        return [Patient.from_row(r) for r in rows]

    @staticmethod
    def count() -> int:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM patients WHERE is_active = 1")
        return row["c"] if row else 0

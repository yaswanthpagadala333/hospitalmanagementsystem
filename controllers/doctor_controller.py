"""
doctor_controller.py
=====================
Business logic for doctor/physician management.
"""

from __future__ import annotations

from typing import Optional

from database.database import db
from models.doctor import Doctor
from utils.helpers import generate_code
from utils.logger import get_logger
from utils.validators import sanitize_search_term

logger = get_logger(__name__)


class DoctorController:

    @staticmethod
    def _next_doctor_code() -> str:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM doctors")
        return generate_code("DOC", (row["c"] if row else 0) + 1)

    @classmethod
    def create(cls, doctor: Doctor) -> Doctor:
        doctor.validate()
        doctor.doctor_code = cls._next_doctor_code()
        query = """
            INSERT INTO doctors
                (doctor_code, first_name, last_name, specialization, department, phone,
                 email, license_number, consultation_fee, years_experience,
                 availability_days, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            doctor.doctor_code, doctor.first_name, doctor.last_name, doctor.specialization,
            doctor.department, doctor.phone, doctor.email, doctor.license_number,
            doctor.consultation_fee, doctor.years_experience, doctor.availability_days,
            int(doctor.is_active),
        )
        cursor = db.execute(query, params)
        doctor.id = cursor.lastrowid
        logger.info("Created doctor #%s (%s)", doctor.id, doctor.doctor_code)
        return doctor

    @staticmethod
    def update(doctor: Doctor) -> None:
        if not doctor.id:
            raise ValueError("Cannot update a doctor without an id.")
        doctor.validate()
        query = """
            UPDATE doctors SET
                first_name=?, last_name=?, specialization=?, department=?, phone=?,
                email=?, license_number=?, consultation_fee=?, years_experience=?,
                availability_days=?, is_active=?
            WHERE id=?
        """
        params = (
            doctor.first_name, doctor.last_name, doctor.specialization, doctor.department,
            doctor.phone, doctor.email, doctor.license_number, doctor.consultation_fee,
            doctor.years_experience, doctor.availability_days, int(doctor.is_active), doctor.id,
        )
        db.execute(query, params)
        logger.info("Updated doctor #%s", doctor.id)

    @staticmethod
    def deactivate(doctor_id: int) -> None:
        db.execute("UPDATE doctors SET is_active = 0 WHERE id = ?", (doctor_id,))

    @staticmethod
    def reactivate(doctor_id: int) -> None:
        db.execute("UPDATE doctors SET is_active = 1 WHERE id = ?", (doctor_id,))

    @staticmethod
    def get_by_id(doctor_id: int) -> Optional[Doctor]:
        row = db.fetch_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
        return Doctor.from_row(row) if row else None

    @staticmethod
    def list_all(include_inactive: bool = False) -> list[Doctor]:
        query = "SELECT * FROM doctors"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY last_name, first_name"
        return [Doctor.from_row(r) for r in db.fetch_all(query)]

    @staticmethod
    def list_by_department(department: str) -> list[Doctor]:
        rows = db.fetch_all(
            "SELECT * FROM doctors WHERE department = ? AND is_active = 1 ORDER BY last_name",
            (department,),
        )
        return [Doctor.from_row(r) for r in rows]

    @staticmethod
    def search(term: str) -> list[Doctor]:
        term = sanitize_search_term(term)
        like = f"%{term}%"
        query = """
            SELECT * FROM doctors
            WHERE is_active = 1 AND (
                first_name LIKE ? OR last_name LIKE ? OR doctor_code LIKE ?
                OR specialization LIKE ? OR department LIKE ?
            )
            ORDER BY last_name, first_name
        """
        rows = db.fetch_all(query, (like, like, like, like, like))
        return [Doctor.from_row(r) for r in rows]

    @staticmethod
    def list_departments() -> list[str]:
        rows = db.fetch_all("SELECT DISTINCT department FROM doctors ORDER BY department")
        return [r["department"] for r in rows]

    @staticmethod
    def count() -> int:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM doctors WHERE is_active = 1")
        return row["c"] if row else 0

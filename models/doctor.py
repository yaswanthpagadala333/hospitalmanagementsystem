"""
doctor.py
=========
Domain model for a hospital doctor/physician.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from utils import validators
from utils.validators import require


@dataclass
class Doctor:
    first_name: str
    last_name: str
    specialization: str
    department: str
    phone: str
    license_number: str
    email: Optional[str] = None
    consultation_fee: float = 0.0
    years_experience: int = 0
    availability_days: str = "Mon,Tue,Wed,Thu,Fri"
    is_active: bool = True
    doctor_code: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def validate(self) -> None:
        require(validators.is_valid_name(self.first_name), "First name is invalid.")
        require(validators.is_valid_name(self.last_name), "Last name is invalid.")
        require(bool(self.specialization and self.specialization.strip()), "Specialization is required.")
        require(bool(self.department and self.department.strip()), "Department is required.")
        require(validators.is_valid_phone(self.phone), "Phone number is invalid.")
        require(validators.is_valid_license(self.license_number), "License number must look like ABC-12345.")
        require(self.consultation_fee >= 0, "Consultation fee cannot be negative.")
        require(self.years_experience >= 0, "Years of experience cannot be negative.")
        if self.email:
            require(validators.is_valid_email(self.email), "Email address is invalid.")

    @property
    def full_name(self) -> str:
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def availability_list(self) -> list[str]:
        return [d.strip() for d in self.availability_days.split(",") if d.strip()]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Doctor":
        data = dict(row)
        data["is_active"] = bool(data.get("is_active", 1))
        return cls(**data)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "doctor_code": self.doctor_code,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "specialization": self.specialization,
            "department": self.department,
            "phone": self.phone,
            "email": self.email,
            "license_number": self.license_number,
            "consultation_fee": self.consultation_fee,
            "years_experience": self.years_experience,
            "availability_days": self.availability_days,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

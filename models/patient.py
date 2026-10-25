"""
patient.py
==========
Domain model for a hospital patient. A ``Patient`` is a plain dataclass
that knows how to validate itself and convert to/from SQLite rows and
plain dictionaries — it deliberately has no knowledge of the database
connection or the GUI (that belongs to the controller / view layers,
keeping this a clean, easily unit-testable domain object).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from utils import validators
from utils.validators import require


@dataclass
class Patient:
    first_name: str
    last_name: str
    date_of_birth: str            # ISO format YYYY-MM-DD
    gender: str                   # Male | Female | Other
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies: Optional[str] = None
    is_active: bool = True
    patient_code: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Raise ``ValidationError`` if any field is invalid. Called by the
        controller before every insert/update."""
        require(validators.is_valid_name(self.first_name), "First name is invalid.")
        require(validators.is_valid_name(self.last_name), "Last name is invalid.")
        require(validators.is_valid_date(self.date_of_birth), "Date of birth must be YYYY-MM-DD.")
        require(validators.is_past_or_today(self.date_of_birth), "Date of birth cannot be in the future.")
        require(self.gender in ("Male", "Female", "Other"), "Gender must be Male, Female, or Other.")
        require(validators.is_valid_phone(self.phone), "Phone number is invalid.")
        if self.email:
            require(validators.is_valid_email(self.email), "Email address is invalid.")
        if self.blood_group:
            require(validators.is_valid_blood_group(self.blood_group), "Blood group is invalid.")
        if self.emergency_contact_phone:
            require(validators.is_valid_phone(self.emergency_contact_phone), "Emergency contact phone is invalid.")

    # ------------------------------------------------------------------
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        return validators.calculate_age(self.date_of_birth)

    # ------------------------------------------------------------------
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Patient":
        data = dict(row)
        data["is_active"] = bool(data.get("is_active", 1))
        return cls(**data)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_code": self.patient_code,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "blood_group": self.blood_group,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "allergies": self.allergies,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

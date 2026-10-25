"""
user.py
=======
Domain model for a system/staff user account (login + role-based access).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from config import config
from utils import validators
from utils.validators import require


@dataclass
class User:
    username: str
    full_name: str
    role: str
    password_hash: Optional[str] = None
    salt: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None

    def validate(self) -> None:
        require(bool(self.username and len(self.username.strip()) >= 3), "Username must be at least 3 characters.")
        require(bool(self.full_name and self.full_name.strip()), "Full name is required.")
        require(self.role in config.ALL_ROLES, f"Role must be one of {config.ALL_ROLES}.")
        if self.email:
            require(validators.is_valid_email(self.email), "Email address is invalid.")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        data = dict(row)
        data["is_active"] = bool(data.get("is_active", 1))
        return cls(**data)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
            data["salt"] = self.salt
        return data

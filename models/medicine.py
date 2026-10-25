"""
medicine.py
===========
Domain model for a pharmacy inventory item.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from utils import validators
from utils.validators import require


@dataclass
class Medicine:
    name: str
    category: str
    unit_price: float
    stock_quantity: int = 0
    reorder_level: int = 20
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    medicine_code: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    def validate(self) -> None:
        require(bool(self.name and self.name.strip()), "Medicine name is required.")
        require(bool(self.category and self.category.strip()), "Category is required.")
        require(self.unit_price >= 0, "Unit price cannot be negative.")
        require(self.stock_quantity >= 0, "Stock quantity cannot be negative.")
        require(self.reorder_level >= 0, "Reorder level cannot be negative.")
        if self.expiry_date:
            require(validators.is_valid_date(self.expiry_date), "Expiry date must be YYYY-MM-DD.")

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.reorder_level

    @property
    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        from datetime import date
        return date.fromisoformat(self.expiry_date) < date.today()

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Medicine":
        return cls(**dict(row))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "medicine_code": self.medicine_code,
            "name": self.name,
            "category": self.category,
            "manufacturer": self.manufacturer,
            "unit_price": self.unit_price,
            "stock_quantity": self.stock_quantity,
            "reorder_level": self.reorder_level,
            "batch_number": self.batch_number,
            "expiry_date": self.expiry_date,
            "is_low_stock": self.is_low_stock,
            "is_expired": self.is_expired,
            "created_at": self.created_at,
        }

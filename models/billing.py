"""
billing.py
==========
Domain models for invoices: ``BillItem`` (a single line item) and
``Bill`` (the invoice header aggregating items, tax, and totals).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from utils.validators import require

VALID_ITEM_TYPES = ("Consultation", "Medicine", "Test", "Procedure", "Other")
VALID_PAYMENT_STATUSES = ("Unpaid", "Paid", "Partially Paid", "Refunded")
VALID_PAYMENT_METHODS = ("Cash", "Card", "Insurance", "Online")


@dataclass
class BillItem:
    description: str
    item_type: str
    quantity: int
    unit_price: float
    amount: float = 0.0
    id: Optional[int] = None
    bill_id: Optional[int] = None
    # Set only when this line item was picked from pharmacy inventory
    # (see BillingView._add_medicine_item). Not a persisted column on
    # bill_items — used solely by BillingController.create_bill to
    # decrement inventory stock atomically alongside the bill insert.
    medicine_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.amount:
            self.amount = round(self.quantity * self.unit_price, 2)

    def validate(self) -> None:
        require(bool(self.description and self.description.strip()), "Item description is required.")
        require(self.item_type in VALID_ITEM_TYPES, f"Item type must be one of {VALID_ITEM_TYPES}.")
        require(self.quantity > 0, "Quantity must be positive.")
        require(self.unit_price >= 0, "Unit price cannot be negative.")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "BillItem":
        return cls(**dict(row))

    def to_dict(self) -> dict:
        return {
            "id": self.id, "bill_id": self.bill_id, "description": self.description,
            "item_type": self.item_type, "quantity": self.quantity,
            "unit_price": self.unit_price, "amount": self.amount,
        }


@dataclass
class Bill:
    patient_id: int
    items: list[BillItem] = field(default_factory=list)
    appointment_id: Optional[int] = None
    tax_percent: float = 5.0
    discount_amount: float = 0.0
    payment_status: str = "Unpaid"
    payment_method: Optional[str] = None
    bill_number: Optional[str] = None
    id: Optional[int] = None
    bill_date: Optional[str] = None
    created_at: Optional[str] = None

    # Populated for display only.
    patient_name: Optional[str] = None

    def validate(self) -> None:
        require(isinstance(self.patient_id, int) and self.patient_id > 0, "A valid patient must be selected.")
        require(len(self.items) > 0, "A bill must have at least one line item.")
        require(self.tax_percent >= 0, "Tax percent cannot be negative.")
        require(self.discount_amount >= 0, "Discount cannot be negative.")
        require(self.payment_status in VALID_PAYMENT_STATUSES, f"Payment status must be one of {VALID_PAYMENT_STATUSES}.")
        if self.payment_method:
            require(self.payment_method in VALID_PAYMENT_METHODS, f"Payment method must be one of {VALID_PAYMENT_METHODS}.")
        for item in self.items:
            item.validate()

    @property
    def subtotal(self) -> float:
        return round(sum(item.amount for item in self.items), 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * (self.tax_percent / 100), 2)

    @property
    def total_amount(self) -> float:
        return round(self.subtotal + self.tax_amount - self.discount_amount, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bill_number": self.bill_number,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "appointment_id": self.appointment_id,
            "bill_date": self.bill_date,
            "subtotal": self.subtotal,
            "tax_percent": self.tax_percent,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
        }

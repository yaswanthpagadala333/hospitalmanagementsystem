"""
medicine_controller.py
=======================
Business logic for pharmacy inventory: CRUD, stock adjustments, low-stock
and expiry alerts, and prescription-driven stock deduction.
"""

from __future__ import annotations

from typing import Optional

from database.database import db
from models.medicine import Medicine
from utils.helpers import generate_code
from utils.logger import get_logger
from utils.validators import require, sanitize_search_term

logger = get_logger(__name__)


class MedicineController:

    @staticmethod
    def _next_medicine_code() -> str:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM medicines")
        return generate_code("MED", (row["c"] if row else 0) + 1)

    @classmethod
    def create(cls, medicine: Medicine) -> Medicine:
        medicine.validate()
        medicine.medicine_code = cls._next_medicine_code()
        query = """
            INSERT INTO medicines
                (medicine_code, name, category, manufacturer, unit_price,
                 stock_quantity, reorder_level, batch_number, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            medicine.medicine_code, medicine.name, medicine.category, medicine.manufacturer,
            medicine.unit_price, medicine.stock_quantity, medicine.reorder_level,
            medicine.batch_number, medicine.expiry_date,
        )
        cursor = db.execute(query, params)
        medicine.id = cursor.lastrowid
        logger.info("Added medicine #%s (%s)", medicine.id, medicine.medicine_code)
        return medicine

    @staticmethod
    def update(medicine: Medicine) -> None:
        if not medicine.id:
            raise ValueError("Cannot update a medicine without an id.")
        medicine.validate()
        query = """
            UPDATE medicines SET
                name=?, category=?, manufacturer=?, unit_price=?, stock_quantity=?,
                reorder_level=?, batch_number=?, expiry_date=?
            WHERE id=?
        """
        params = (
            medicine.name, medicine.category, medicine.manufacturer, medicine.unit_price,
            medicine.stock_quantity, medicine.reorder_level, medicine.batch_number,
            medicine.expiry_date, medicine.id,
        )
        db.execute(query, params)
        logger.info("Updated medicine #%s", medicine.id)

    @staticmethod
    def delete(medicine_id: int) -> None:
        db.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
        logger.info("Deleted medicine #%s", medicine_id)

    @staticmethod
    def adjust_stock(medicine_id: int, delta: int, reason: str = "") -> None:
        """Increase (delta > 0) or decrease (delta < 0) stock, rejecting any
        operation that would drive stock negative."""
        medicine = MedicineController.get_by_id(medicine_id)
        if medicine is None:
            raise ValueError("Medicine not found.")
        new_qty = medicine.stock_quantity + delta
        require(new_qty >= 0, f"Insufficient stock for {medicine.name}: only {medicine.stock_quantity} left.")
        db.execute("UPDATE medicines SET stock_quantity = ? WHERE id = ?", (new_qty, medicine_id))
        logger.info("Stock for medicine #%s adjusted by %+d (%s) -> %d", medicine_id, delta, reason, new_qty)

    @staticmethod
    def get_by_id(medicine_id: int) -> Optional[Medicine]:
        row = db.fetch_one("SELECT * FROM medicines WHERE id = ?", (medicine_id,))
        return Medicine.from_row(row) if row else None

    @staticmethod
    def list_all() -> list[Medicine]:
        rows = db.fetch_all("SELECT * FROM medicines ORDER BY name")
        return [Medicine.from_row(r) for r in rows]

    @staticmethod
    def search(term: str) -> list[Medicine]:
        term = sanitize_search_term(term)
        like = f"%{term}%"
        rows = db.fetch_all(
            "SELECT * FROM medicines WHERE name LIKE ? OR category LIKE ? OR medicine_code LIKE ? ORDER BY name",
            (like, like, like),
        )
        return [Medicine.from_row(r) for r in rows]

    @staticmethod
    def low_stock_items() -> list[Medicine]:
        rows = db.fetch_all("SELECT * FROM medicines WHERE stock_quantity <= reorder_level ORDER BY stock_quantity")
        return [Medicine.from_row(r) for r in rows]

    @staticmethod
    def expiring_soon(within_days: int = 60) -> list[Medicine]:
        rows = db.fetch_all(
            """
            SELECT * FROM medicines
            WHERE expiry_date IS NOT NULL
              AND date(expiry_date) <= date('now', ?)
            ORDER BY expiry_date
            """,
            (f"+{within_days} days",),
        )
        return [Medicine.from_row(r) for r in rows]

    @staticmethod
    def list_categories() -> list[str]:
        rows = db.fetch_all("SELECT DISTINCT category FROM medicines ORDER BY category")
        return [r["category"] for r in rows]

    @staticmethod
    def count() -> int:
        row = db.fetch_one("SELECT COUNT(*) AS c FROM medicines")
        return row["c"] if row else 0

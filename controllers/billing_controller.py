"""
billing_controller.py
======================
Business logic for invoicing: creating bills with line items inside a
single atomic transaction, recording payments, and querying billing
history / revenue figures used by the analytics module.
"""

from __future__ import annotations

from typing import Optional

from database.database import db, DatabaseError
from models.billing import Bill, BillItem
from utils.helpers import generate_bill_number
from utils.logger import get_logger
from utils.validators import require

logger = get_logger(__name__)

_SELECT_BILL_JOINED = """
    SELECT b.*, (p.first_name || ' ' || p.last_name) AS patient_name
    FROM bills b
    JOIN patients p ON p.id = b.patient_id
"""


class BillingController:

    @classmethod
    def create_bill(cls, bill: Bill) -> Bill:
        """Persist a bill and its line items atomically: either everything
        commits, or (on any failure) nothing does."""
        bill.validate()
        bill.bill_number = generate_bill_number()

        conn = db.connection
        try:
            with db.transaction():
                cursor = conn.execute(
                    """
                    INSERT INTO bills
                        (bill_number, patient_id, appointment_id, subtotal, tax_percent,
                         tax_amount, discount_amount, total_amount, payment_status, payment_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bill.bill_number, bill.patient_id, bill.appointment_id, bill.subtotal,
                        bill.tax_percent, bill.tax_amount, bill.discount_amount, bill.total_amount,
                        bill.payment_status, bill.payment_method,
                    ),
                )
                bill.id = cursor.lastrowid
                for item in bill.items:
                    conn.execute(
                        """
                        INSERT INTO bill_items (bill_id, description, item_type, quantity, unit_price, amount)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (bill.id, item.description, item.item_type, item.quantity, item.unit_price, item.amount),
                    )
                    # Line items picked from pharmacy inventory (see
                    # BillingView._add_medicine_item) carry a medicine_id;
                    # deduct the dispensed quantity from stock as part of
                    # the same transaction so a bill can never be created
                    # without the corresponding stock leaving inventory,
                    # and a stock shortfall rolls back the whole bill.
                    if item.medicine_id is not None:
                        row = conn.execute(
                            "SELECT name, stock_quantity FROM medicines WHERE id = ?", (item.medicine_id,)
                        ).fetchone()
                        require(row is not None, f"Medicine #{item.medicine_id} no longer exists.")
                        new_qty = row["stock_quantity"] - item.quantity
                        require(
                            new_qty >= 0,
                            f"Insufficient stock for {row['name']}: only {row['stock_quantity']} left.",
                        )
                        conn.execute(
                            "UPDATE medicines SET stock_quantity = ? WHERE id = ?", (new_qty, item.medicine_id)
                        )
        except DatabaseError:
            logger.exception("Failed to create bill for patient #%s", bill.patient_id)
            raise

        logger.info("Created bill %s for patient #%s, total=%.2f", bill.bill_number, bill.patient_id, bill.total_amount)
        return bill

    @staticmethod
    def record_payment(bill_id: int, payment_status: str, payment_method: Optional[str] = None) -> None:
        db.execute(
            "UPDATE bills SET payment_status = ?, payment_method = COALESCE(?, payment_method) WHERE id = ?",
            (payment_status, payment_method, bill_id),
        )
        logger.info("Bill #%s payment status -> %s", bill_id, payment_status)

    @staticmethod
    def get_by_id(bill_id: int) -> Optional[Bill]:
        row = db.fetch_one(_SELECT_BILL_JOINED + " WHERE b.id = ?", (bill_id,))
        if not row:
            return None
        item_rows = db.fetch_all("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,))
        return BillingController._row_to_bill(row, item_rows)

    @staticmethod
    def _row_to_bill(row, item_rows) -> Bill:
        data = dict(row)
        patient_name = data.pop("patient_name", None)
        items = [BillItem.from_row(r) for r in item_rows]
        bill = Bill(
            id=data["id"], bill_number=data["bill_number"], patient_id=data["patient_id"],
            appointment_id=data["appointment_id"], items=items, tax_percent=data["tax_percent"],
            discount_amount=data["discount_amount"], payment_status=data["payment_status"],
            payment_method=data["payment_method"], bill_date=data["bill_date"], created_at=data["created_at"],
        )
        bill.patient_name = patient_name
        return bill

    @staticmethod
    def list_all() -> list[Bill]:
        rows = db.fetch_all(_SELECT_BILL_JOINED + " ORDER BY b.bill_date DESC")
        bills = []
        for row in rows:
            item_rows = db.fetch_all("SELECT * FROM bill_items WHERE bill_id = ?", (row["id"],))
            bills.append(BillingController._row_to_bill(row, item_rows))
        return bills

    @staticmethod
    def list_for_patient(patient_id: int) -> list[Bill]:
        rows = db.fetch_all(_SELECT_BILL_JOINED + " WHERE b.patient_id = ? ORDER BY b.bill_date DESC", (patient_id,))
        bills = []
        for row in rows:
            item_rows = db.fetch_all("SELECT * FROM bill_items WHERE bill_id = ?", (row["id"],))
            bills.append(BillingController._row_to_bill(row, item_rows))
        return bills

    @staticmethod
    def list_unpaid() -> list[Bill]:
        rows = db.fetch_all(
            _SELECT_BILL_JOINED + " WHERE b.payment_status IN ('Unpaid', 'Partially Paid') ORDER BY b.bill_date",
        )
        bills = []
        for row in rows:
            item_rows = db.fetch_all("SELECT * FROM bill_items WHERE bill_id = ?", (row["id"],))
            bills.append(BillingController._row_to_bill(row, item_rows))
        return bills

    @staticmethod
    def total_revenue() -> float:
        row = db.fetch_one("SELECT COALESCE(SUM(total_amount), 0) AS total FROM bills WHERE payment_status = 'Paid'")
        return float(row["total"]) if row else 0.0

    @staticmethod
    def total_outstanding() -> float:
        row = db.fetch_one(
            "SELECT COALESCE(SUM(total_amount), 0) AS total FROM bills WHERE payment_status != 'Paid'"
        )
        return float(row["total"]) if row else 0.0

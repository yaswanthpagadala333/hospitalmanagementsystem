"""
analytics_engine.py
====================
Turns raw SQLite tables into ``pandas`` DataFrames and computes the
statistics shown on the dashboard and analytics screens. Kept separate
from ``charts.py`` so the numbers themselves are unit-testable without
touching matplotlib at all.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from database.database import db
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsEngine:
    """Read-only analytical queries over the hospital database, expressed
    as pandas DataFrames so aggregation/grouping stays declarative."""

    # ------------------------------------------------------------------
    # DataFrame loaders
    # ------------------------------------------------------------------
    @staticmethod
    def _query_df(query: str, params: tuple = ()) -> pd.DataFrame:
        rows = db.fetch_all(query, params)
        return pd.DataFrame([dict(r) for r in rows])

    @classmethod
    def patients_df(cls) -> pd.DataFrame:
        return cls._query_df("SELECT * FROM patients")

    @classmethod
    def appointments_df(cls) -> pd.DataFrame:
        return cls._query_df(
            """
            SELECT a.*, d.department, d.specialization,
                   (d.first_name || ' ' || d.last_name) AS doctor_name
            FROM appointments a JOIN doctors d ON d.id = a.doctor_id
            """
        )

    @classmethod
    def bills_df(cls) -> pd.DataFrame:
        return cls._query_df("SELECT * FROM bills")

    @classmethod
    def medicines_df(cls) -> pd.DataFrame:
        return cls._query_df("SELECT * FROM medicines")

    @classmethod
    def bill_items_df(cls) -> pd.DataFrame:
        return cls._query_df("SELECT * FROM bill_items")

    # ------------------------------------------------------------------
    # KPIs used on the dashboard's stat cards
    # ------------------------------------------------------------------
    @classmethod
    def kpi_summary(cls) -> dict:
        patients = cls.patients_df()
        appts = cls.appointments_df()
        bills = cls.bills_df()
        meds = cls.medicines_df()

        total_revenue = float(bills.loc[bills["payment_status"] == "Paid", "total_amount"].sum()) if not bills.empty else 0.0
        outstanding = float(bills.loc[bills["payment_status"] != "Paid", "total_amount"].sum()) if not bills.empty else 0.0
        avg_bill = float(bills["total_amount"].mean()) if not bills.empty else 0.0

        return {
            "total_patients": int((patients["is_active"] == 1).sum()) if not patients.empty else 0,
            "total_appointments": int(len(appts)),
            "completed_appointments": int((appts["status"] == "Completed").sum()) if not appts.empty else 0,
            "cancelled_appointments": int((appts["status"] == "Cancelled").sum()) if not appts.empty else 0,
            "total_revenue": round(total_revenue, 2),
            "outstanding_amount": round(outstanding, 2),
            "average_bill_value": round(avg_bill, 2),
            "low_stock_count": int((meds["stock_quantity"] <= meds["reorder_level"]).sum()) if not meds.empty else 0,
            "total_medicines": int(len(meds)),
        }

    # ------------------------------------------------------------------
    # Time series / group-bys used by charts
    # ------------------------------------------------------------------
    @classmethod
    def revenue_by_day(cls, last_n_days: int = 30) -> pd.DataFrame:
        bills = cls.bills_df()
        if bills.empty:
            return pd.DataFrame(columns=["date", "revenue"])
        bills["date"] = pd.to_datetime(bills["bill_date"]).dt.date
        paid = bills[bills["payment_status"] == "Paid"]
        grouped = paid.groupby("date")["total_amount"].sum().reset_index()
        grouped.columns = ["date", "revenue"]
        grouped = grouped.sort_values("date").tail(last_n_days)
        return grouped

    @classmethod
    def appointments_by_department(cls) -> pd.DataFrame:
        appts = cls.appointments_df()
        if appts.empty:
            return pd.DataFrame(columns=["department", "count"])
        grouped = appts.groupby("department").size().reset_index(name="count")
        return grouped.sort_values("count", ascending=False)

    @classmethod
    def appointments_by_status(cls) -> pd.DataFrame:
        appts = cls.appointments_df()
        if appts.empty:
            return pd.DataFrame(columns=["status", "count"])
        grouped = appts.groupby("status").size().reset_index(name="count")
        return grouped

    @classmethod
    def patient_age_distribution(cls) -> pd.DataFrame:
        patients = cls.patients_df()
        if patients.empty:
            return pd.DataFrame(columns=["age"])
        dob = pd.to_datetime(patients["date_of_birth"])
        today = pd.Timestamp.now()
        ages = ((today - dob).dt.days / 365.25).apply(np.floor).astype(int)
        return pd.DataFrame({"age": ages})

    @classmethod
    def patient_gender_split(cls) -> pd.DataFrame:
        patients = cls.patients_df()
        if patients.empty:
            return pd.DataFrame(columns=["gender", "count"])
        grouped = patients.groupby("gender").size().reset_index(name="count")
        return grouped

    @classmethod
    def top_medicines_by_usage(cls, top_n: int = 8) -> pd.DataFrame:
        items = cls.bill_items_df()
        if items.empty:
            return pd.DataFrame(columns=["description", "quantity"])
        meds_only = items[items["item_type"] == "Medicine"]
        grouped = meds_only.groupby("description")["quantity"].sum().reset_index()
        grouped = grouped.sort_values("quantity", ascending=False).head(top_n)
        return grouped

    @classmethod
    def doctor_workload(cls) -> pd.DataFrame:
        appts = cls.appointments_df()
        if appts.empty:
            return pd.DataFrame(columns=["doctor_name", "count"])
        grouped = appts.groupby("doctor_name").size().reset_index(name="count")
        return grouped.sort_values("count", ascending=False)

    @classmethod
    def stock_levels(cls) -> pd.DataFrame:
        meds = cls.medicines_df()
        if meds.empty:
            return pd.DataFrame(columns=["name", "stock_quantity", "reorder_level"])
        return meds[["name", "stock_quantity", "reorder_level"]].sort_values("stock_quantity")

    @classmethod
    def revenue_statistics(cls) -> dict:
        """Descriptive statistics (mean/median/std/percentiles) over paid
        bill totals, computed with numpy for a clear demonstration of
        vectorised numeric analysis."""
        bills = cls.bills_df()
        if bills.empty:
            return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0, "p90": 0}
        values = bills.loc[bills["payment_status"] == "Paid", "total_amount"].to_numpy(dtype=float)
        if values.size == 0:
            return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0, "p90": 0}
        return {
            "mean": round(float(np.mean(values)), 2),
            "median": round(float(np.median(values)), 2),
            "std": round(float(np.std(values)), 2),
            "min": round(float(np.min(values)), 2),
            "max": round(float(np.max(values)), 2),
            "p90": round(float(np.percentile(values, 90)), 2),
        }

"""
charts.py
=========
Builds ``matplotlib`` Figures (styled with ``seaborn``) from the
DataFrames produced by ``AnalyticsEngine``. Each function returns a
``Figure`` object rather than calling ``plt.show()``, so the caller can
either embed it in CustomTkinter via ``FigureCanvasTkAgg`` or save it to
disk for a PDF/PNG report — the chart logic itself has no GUI dependency.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # safe default; the GUI layer switches backends as needed for embedding

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from analytics.analytics_engine import AnalyticsEngine
from utils.logger import get_logger

logger = get_logger(__name__)

sns.set_theme(style="whitegrid", palette="deep")
_FIG_FACECOLOR = "#FFFFFF"
_ACCENT = "#2E86C1"


def _new_figure(figsize=(6.4, 4.0)) -> tuple[Figure, plt.Axes]:
    fig = Figure(figsize=figsize, dpi=100, facecolor=_FIG_FACECOLOR)
    ax = fig.add_subplot(111)
    return fig, ax


def revenue_trend_chart(days: int = 30) -> Figure:
    df = AnalyticsEngine.revenue_by_day(days)
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No revenue data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig

    dates = pd.to_datetime(df["date"])
    sns.lineplot(x=dates, y=df["revenue"], marker="o", ax=ax, color=_ACCENT, linewidth=2)
    ax.fill_between(dates, df["revenue"], alpha=0.12, color=_ACCENT)
    ax.set_title(f"Revenue Trend (Last {days} Days)", fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue")

    # With very few points, let matplotlib's default locator misbehave
    # (it can span years); pin a sensible day-level range/format instead.
    span = (dates.max() - dates.min()).days if len(dates) > 1 else 0
    if span <= 1:
        pad = pd.Timedelta(days=3)
        ax.set_xlim(dates.min() - pad, dates.max() + pad)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    return fig


def appointments_by_department_chart() -> Figure:
    df = AnalyticsEngine.appointments_by_department()
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No appointment data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    sns.barplot(data=df, x="count", y="department", hue="department", legend=False, ax=ax, palette="Blues_d")
    ax.set_title("Appointments by Department", fontweight="bold")
    ax.set_xlabel("Appointments")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


def appointments_by_status_chart() -> Figure:
    df = AnalyticsEngine.appointments_by_status()
    fig, ax = _new_figure(figsize=(5.2, 4.2))
    if df.empty:
        ax.text(0.5, 0.5, "No appointment data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    colors_map = {"Scheduled": "#2E86C1", "Completed": "#28B463", "Cancelled": "#E74C3C", "No-Show": "#F39C12"}
    colors = [colors_map.get(s, "#95A5A6") for s in df["status"]]
    ax.pie(df["count"], labels=df["status"], autopct="%1.0f%%", colors=colors,
           startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title("Appointment Status Breakdown", fontweight="bold")
    fig.tight_layout()
    return fig


def patient_age_distribution_chart() -> Figure:
    df = AnalyticsEngine.patient_age_distribution()
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No patient data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    sns.histplot(df["age"], bins=12, kde=True, ax=ax, color=_ACCENT)
    ax.set_title("Patient Age Distribution", fontweight="bold")
    ax.set_xlabel("Age")
    ax.set_ylabel("Number of Patients")
    fig.tight_layout()
    return fig


def patient_gender_split_chart() -> Figure:
    df = AnalyticsEngine.patient_gender_split()
    fig, ax = _new_figure(figsize=(5.2, 4.2))
    if df.empty:
        ax.text(0.5, 0.5, "No patient data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    colors_map = {"Male": "#2E86C1", "Female": "#EB6FA6", "Other": "#8E44AD"}
    colors = [colors_map.get(g, "#95A5A6") for g in df["gender"]]
    ax.pie(df["count"], labels=df["gender"], autopct="%1.0f%%", colors=colors,
           startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title("Patient Gender Split", fontweight="bold")
    fig.tight_layout()
    return fig


def top_medicines_chart() -> Figure:
    df = AnalyticsEngine.top_medicines_by_usage()
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No prescription data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    sns.barplot(data=df, x="quantity", y="description", hue="description", legend=False, ax=ax, palette="Greens_d")
    ax.set_title("Top Medicines by Quantity Dispensed", fontweight="bold")
    ax.set_xlabel("Quantity")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


def doctor_workload_chart() -> Figure:
    df = AnalyticsEngine.doctor_workload()
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No appointment data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    sns.barplot(data=df, x="count", y="doctor_name", hue="doctor_name", legend=False, ax=ax, palette="Purples_d")
    ax.set_title("Doctor Workload (Total Appointments)", fontweight="bold")
    ax.set_xlabel("Appointments")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


def stock_levels_chart(top_n: int = 12) -> Figure:
    df = AnalyticsEngine.stock_levels().head(top_n)
    fig, ax = _new_figure()
    if df.empty:
        ax.text(0.5, 0.5, "No inventory data yet", ha="center", va="center", fontsize=11, color="grey")
        ax.set_axis_off()
        return fig
    bar_colors = ["#E74C3C" if row.stock_quantity <= row.reorder_level else "#28B463" for row in df.itertuples()]
    ax.barh(df["name"], df["stock_quantity"], color=bar_colors)
    ax.axvline(df["reorder_level"].mean(), color="grey", linestyle="--", linewidth=1, label="Avg. reorder level")
    ax.set_title("Inventory Stock Levels (red = at/below reorder level)", fontweight="bold")
    ax.set_xlabel("Units in Stock")
    fig.tight_layout()
    return fig


def save_figure(fig: Figure, path) -> None:
    """Persist a chart figure to disk (used by report/export features)."""
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    logger.info("Saved chart to %s", path)

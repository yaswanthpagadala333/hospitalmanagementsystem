"""
analytics_view.py
==================
Full analytics dashboard: a grid of matplotlib/seaborn charts plus a
numeric summary table (built with numpy/pandas in ``AnalyticsEngine``),
giving a management-level view of hospital operations.
"""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analytics.analytics_engine import AnalyticsEngine
from analytics import charts
from models.user import User
from utils.helpers import format_currency


class AnalyticsView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._canvases: list[FigureCanvasTkAgg] = []
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Analytics", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Refresh", command=self.refresh, width=100,
                      fg_color="gray50", hover_color="gray40").pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self.stats_frame = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=("gray95", "gray17"))
        self.stats_frame.pack(fill="x", pady=(0, 14))

        self.grid_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        self.grid_frame.grid_columnconfigure(0, weight=1, uniform="charts")
        self.grid_frame.grid_columnconfigure(1, weight=1, uniform="charts")

    def on_show(self) -> None:
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._refresh_stats()
        self._refresh_charts()

    def _refresh_stats(self) -> None:
        for child in self.stats_frame.winfo_children():
            child.destroy()

        ctk.CTkLabel(self.stats_frame, text="Revenue Statistics (Paid Bills)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        stats = AnalyticsEngine.revenue_statistics()
        row = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        labels = [
            ("Mean", format_currency(stats["mean"])),
            ("Median", format_currency(stats["median"])),
            ("Std. Dev.", format_currency(stats["std"])),
            ("Min", format_currency(stats["min"])),
            ("Max", format_currency(stats["max"])),
            ("90th Percentile", format_currency(stats["p90"])),
        ]
        for i, (label, value) in enumerate(labels):
            cell = ctk.CTkFrame(row, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="w", padx=(0, 22))
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11), text_color=("gray40", "gray60")).pack(anchor="w")
            ctk.CTkLabel(cell, text=value, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w")

    def _refresh_charts(self) -> None:
        for canvas in self._canvases:
            canvas.get_tk_widget().destroy()
        self._canvases.clear()
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        chart_specs = [
            ("Revenue Trend", charts.revenue_trend_chart, dict(days=30)),
            ("Appointment Status", charts.appointments_by_status_chart, {}),
            ("Appointments by Department", charts.appointments_by_department_chart, {}),
            ("Doctor Workload", charts.doctor_workload_chart, {}),
            ("Patient Age Distribution", charts.patient_age_distribution_chart, {}),
            ("Patient Gender Split", charts.patient_gender_split_chart, {}),
            ("Top Medicines Dispensed", charts.top_medicines_chart, {}),
            ("Inventory Stock Levels", charts.stock_levels_chart, {}),
        ]

        for idx, (title, func, kwargs) in enumerate(chart_specs):
            row, col = divmod(idx, 2)
            card = ctk.CTkFrame(self.grid_frame, corner_radius=14, fg_color=("gray95", "gray17"))
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            fig = func(**kwargs)
            fig.set_size_inches(5.6, 3.6)
            canvas = FigureCanvasTkAgg(fig, master=card)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
            self._canvases.append(canvas)

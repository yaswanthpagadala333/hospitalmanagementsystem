"""
dashboard_view.py
==================
Landing screen after login: at-a-glance KPI cards, today's appointment
schedule, and a summary chart. Data is refreshed every time the tab is
shown (see ``on_show``) so it never goes stale during a session.
"""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analytics.analytics_engine import AnalyticsEngine
from analytics import charts
from config import config
from controllers.appointment_controller import AppointmentController
from models.user import User
from utils.helpers import format_currency, today_iso
from views.widgets.stat_card import StatCard


class DashboardView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._chart_canvases: list[FigureCanvasTkAgg] = []
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)
        self._scroll = scroll

        first_name = self.user.full_name.split()[0] if self.user.full_name else self.user.username
        ctk.CTkLabel(scroll, text=f"Welcome back, {first_name} \U0001F44B",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(scroll, text=f"Here's what's happening today, {today_iso()}.",
                     font=ctk.CTkFont(size=13), text_color=("gray35", "gray65")).pack(anchor="w", pady=(0, 16))

        self.cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.cards_frame.pack(fill="x")
        for i in range(4):
            self.cards_frame.grid_columnconfigure(i, weight=1, uniform="cards")

        self.card_patients = StatCard(self.cards_frame, "Total Patients", "0", config.COLOR_PRIMARY, icon="🧑‍🤝‍🧑")
        self.card_appts_today = StatCard(self.cards_frame, "Today's Appointments", "0", config.COLOR_SUCCESS, icon="📅")
        self.card_revenue = StatCard(self.cards_frame, "Revenue Collected", "$0.00", config.COLOR_ACCENT, icon="💰")
        self.card_low_stock = StatCard(self.cards_frame, "Low Stock Alerts", "0", config.COLOR_DANGER, icon="⚠️")
        for i, card in enumerate((self.card_patients, self.card_appts_today, self.card_revenue, self.card_low_stock)):
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)

        # ---- Second row: today's schedule + chart ---------------------
        lower = ctk.CTkFrame(scroll, fg_color="transparent")
        lower.pack(fill="both", expand=True, pady=(18, 0))
        lower.grid_columnconfigure(0, weight=1, uniform="lower")
        lower.grid_columnconfigure(1, weight=1, uniform="lower")

        schedule_card = ctk.CTkFrame(lower, corner_radius=14, fg_color=("white", "gray17"),
                                      border_width=1, border_color=("gray88", "gray24"))
        schedule_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(schedule_card, text="Today's Schedule", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        self.schedule_list = ctk.CTkScrollableFrame(schedule_card, fg_color="transparent", height=260)
        self.schedule_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        chart_card = ctk.CTkFrame(lower, corner_radius=14, fg_color=("white", "gray17"),
                                   border_width=1, border_color=("gray88", "gray24"))
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(chart_card, text="Revenue Trend", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        self.chart_holder = ctk.CTkFrame(chart_card, fg_color="transparent")
        self.chart_holder.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        kpis = AnalyticsEngine.kpi_summary()
        self.card_patients.update_value(str(kpis["total_patients"]))
        self.card_appts_today.update_value(str(AppointmentController.count_today()))
        self.card_revenue.update_value(format_currency(kpis["total_revenue"]))
        self.card_low_stock.update_value(str(kpis["low_stock_count"]))

        self._refresh_schedule()
        self._refresh_chart()

    def _refresh_schedule(self) -> None:
        for child in self.schedule_list.winfo_children():
            child.destroy()

        appts = AppointmentController.list_for_date(today_iso())
        if not appts:
            ctk.CTkLabel(self.schedule_list, text="No appointments scheduled for today.",
                         text_color=("gray40", "gray60")).pack(pady=20)
            return

        status_colors = {"Scheduled": "#2E86C1", "Completed": "#28B463", "Cancelled": "#E74C3C", "No-Show": "#F39C12"}
        for appt in appts:
            row = ctk.CTkFrame(self.schedule_list, fg_color=("white", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=appt.appointment_time, width=60, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 4), pady=8)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(info, text=appt.patient_name, anchor="w", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info, text=f"with {appt.doctor_name}", anchor="w", font=ctk.CTkFont(size=11),
                         text_color=("gray40", "gray60")).pack(anchor="w")
            ctk.CTkLabel(row, text=appt.status, text_color=status_colors.get(appt.status, "gray"),
                         font=ctk.CTkFont(size=11, weight="bold")).pack(side="right", padx=10)

    def _refresh_chart(self) -> None:
        for canvas in self._chart_canvases:
            canvas.get_tk_widget().destroy()
        self._chart_canvases.clear()

        fig = charts.revenue_trend_chart(days=14)
        fig.set_size_inches(5.6, 3.4)
        canvas = FigureCanvasTkAgg(fig, master=self.chart_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvases.append(canvas)

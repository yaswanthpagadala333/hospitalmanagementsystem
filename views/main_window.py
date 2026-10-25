"""
main_window.py
===============
The application shell shown after a successful login: a persistent
sidebar for navigation plus a content area that swaps between the
feature screens (Dashboard, Patients, Doctors, Appointments, Billing,
Pharmacy, Analytics, Reports, Users). Screens are instantiated lazily
(on first visit) and then cached, so switching tabs is instant after
the first load while startup itself stays fast.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from config import config
from models.user import User
from utils.logger import get_logger

logger = get_logger(__name__)

_NAV_ITEMS = [
    ("dashboard", "🏠", "Dashboard"),
    ("patients", "🧑‍🤝‍🧑", "Patients"),
    ("doctors", "🩺", "Doctors"),
    ("appointments", "📅", "Appointments"),
    ("billing", "💳", "Billing"),
    ("pharmacy", "💊", "Pharmacy"),
    ("analytics", "📊", "Analytics"),
    ("reports", "🧾", "Reports"),
    ("users", "👥", "Users & Access"),
]

# Roles permitted to see each nav item. Admin sees everything.
_ROLE_ACCESS = {
    "dashboard": None,
    "patients": None,
    "doctors": None,
    "appointments": None,
    "billing": {"Admin", "Receptionist"},
    "pharmacy": {"Admin", "Pharmacist"},
    "analytics": {"Admin", "Doctor"},
    "reports": {"Admin", "Doctor", "Receptionist"},
    "users": {"Admin"},
}


def _initials(full_name: str, username: str) -> str:
    source = (full_name or username or "?").strip()
    parts = [p for p in source.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return source[:2].upper()


class MainWindow(ctk.CTkFrame):

    def __init__(self, master, user: User, on_logout: Callable[[], None], **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._on_logout = on_logout
        self._screens: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_indicators: dict[str, ctk.CTkFrame] = {}
        self._active_key: str | None = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()
        self.show_screen("dashboard")

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=("gray93", "gray12"))
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        # ---- Brand header --------------------------------------------------
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(22, 16))
        ctk.CTkLabel(header, text="🏥", font=ctk.CTkFont(size=22)).pack(side="left")
        ctk.CTkLabel(
            header, text=config.settings.hospital_name,
            font=ctk.CTkFont(size=14, weight="bold"), wraplength=170, justify="left",
        ).pack(side="left", padx=(8, 0))

        # ---- Current user card ---------------------------------------------
        user_card = ctk.CTkFrame(sidebar, corner_radius=10, fg_color=config.COLOR_PRIMARY_SOFT)
        user_card.pack(fill="x", padx=14, pady=(0, 16))

        avatar = ctk.CTkFrame(user_card, width=36, height=36, corner_radius=18, fg_color=config.COLOR_PRIMARY)
        avatar.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10)
        avatar.grid_propagate(False)
        ctk.CTkLabel(
            avatar, text=_initials(self.user.full_name, self.user.username),
            font=ctk.CTkFont(size=13, weight="bold"), text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            user_card, text=self.user.full_name or self.user.username,
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(10, 0))

        role_badge_color = config.ROLE_BADGE_COLORS.get(self.user.role, config.COLOR_PRIMARY)
        ctk.CTkLabel(
            user_card, text=self.user.role, font=ctk.CTkFont(size=10, weight="bold"),
            text_color=role_badge_color, anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 10))
        user_card.grid_columnconfigure(1, weight=1)

        # ---- Navigation ------------------------------------------------
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10)

        for key, icon, label in _NAV_ITEMS:
            allowed_roles = _ROLE_ACCESS.get(key)
            if allowed_roles and self.user.role not in allowed_roles:
                continue

            row = ctk.CTkFrame(nav_frame, fg_color="transparent", height=42)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            indicator = ctk.CTkFrame(row, width=3, height=30, corner_radius=2, fg_color="transparent")
            indicator.pack(side="left", fill="y", pady=6)
            self._nav_indicators[key] = indicator

            btn = ctk.CTkButton(
                row, text=f"  {icon}   {label}", anchor="w", height=38, corner_radius=8,
                fg_color="transparent", text_color=("gray20", "gray90"),
                hover_color=("gray85", "gray22"), font=ctk.CTkFont(size=13),
                command=lambda k=key: self.show_screen(k),
            )
            btn.pack(side="left", fill="both", expand=True, padx=(5, 0))
            self._nav_buttons[key] = btn

        # ---- Footer ------------------------------------------------------
        bottom_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkButton(
            bottom_frame, text="⎋  Logout", height=38, corner_radius=8,
            fg_color=config.COLOR_DANGER, hover_color=config.COLOR_DANGER_HOVER,
            command=self._on_logout,
        ).pack(fill="x")

    def _build_content_area(self) -> None:
        self.content_area = ctk.CTkFrame(self, fg_color=("gray97", "gray10"), corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _highlight_nav(self, active_key: str) -> None:
        for key, btn in self._nav_buttons.items():
            indicator = self._nav_indicators.get(key)
            if key == active_key:
                btn.configure(fg_color=config.COLOR_PRIMARY_SOFT, text_color=(config.COLOR_PRIMARY, "white"))
                if indicator:
                    indicator.configure(fg_color=config.COLOR_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "gray90"))
                if indicator:
                    indicator.configure(fg_color="transparent")

    def show_screen(self, key: str) -> None:
        if key == self._active_key:
            return

        for screen in self._screens.values():
            screen.grid_forget()

        if key not in self._screens:
            self._screens[key] = self._create_screen(key)

        screen = self._screens[key]
        screen.grid(row=0, column=0, sticky="nsew")
        if hasattr(screen, "on_show"):
            screen.on_show()

        self._highlight_nav(key)
        self._active_key = key
        logger.debug("Navigated to screen '%s'", key)

    def _create_screen(self, key: str) -> ctk.CTkFrame:
        # Imported lazily to keep application startup fast and to avoid
        # any circular-import risk between views and the main window.
        if key == "dashboard":
            from views.dashboard_view import DashboardView
            return DashboardView(self.content_area, user=self.user)
        if key == "patients":
            from views.patient_view import PatientView
            return PatientView(self.content_area, user=self.user)
        if key == "doctors":
            from views.doctor_view import DoctorView
            return DoctorView(self.content_area, user=self.user)
        if key == "appointments":
            from views.appointment_view import AppointmentView
            return AppointmentView(self.content_area, user=self.user)
        if key == "billing":
            from views.billing_view import BillingView
            return BillingView(self.content_area, user=self.user)
        if key == "pharmacy":
            from views.medicine_view import MedicineView
            return MedicineView(self.content_area, user=self.user)
        if key == "analytics":
            from views.analytics_view import AnalyticsView
            return AnalyticsView(self.content_area, user=self.user)
        if key == "reports":
            from views.reports_view import ReportsView
            return ReportsView(self.content_area, user=self.user)
        if key == "users":
            from views.user_management_view import UserManagementView
            return UserManagementView(self.content_area, user=self.user)
        raise ValueError(f"Unknown screen: {key}")

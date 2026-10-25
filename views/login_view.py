"""
login_view.py
=============
Full-screen login form shown before the main application window. On
success it calls ``on_login_success(User)`` supplied by ``main.py``,
which tears this frame down and builds the ``MainWindow``.

Layout: a wide brand panel on the left (hospital identity, tagline)
and a compact sign-in card on the right — a familiar, modern SaaS
login pattern instead of a single centered box on a flat background.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from config import config
from controllers.user_controller import UserController, AuthenticationError
from models.user import User
from utils.logger import get_logger

logger = get_logger(__name__)


class LoginView(ctk.CTkFrame):

    def __init__(self, master, on_login_success: Callable[[User], None], **kwargs) -> None:
        super().__init__(master, fg_color=("gray95", "gray10"), **kwargs)
        self._on_login_success = on_login_success
        self._show_password = False
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=440)
        self.grid_columnconfigure(1, weight=1)
        self._build_brand_panel()
        self._build_form_panel()

    # ------------------------------------------------------------------
    def _build_brand_panel(self) -> None:
        panel = ctk.CTkFrame(self, corner_radius=0, fg_color=config.COLOR_PRIMARY)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_propagate(False)

        wrapper = ctk.CTkFrame(panel, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.46, anchor="center")

        badge = ctk.CTkFrame(wrapper, width=76, height=76, corner_radius=20, fg_color=("white", "white"))
        badge.pack(pady=(0, 22))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="🏥", font=ctk.CTkFont(size=34)).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            wrapper, text=config.settings.hospital_name,
            font=ctk.CTkFont(size=26, weight="bold"), text_color="white",
            wraplength=340, justify="center",
        ).pack()

        ctk.CTkLabel(
            wrapper, text="Hospital Management System",
            font=ctk.CTkFont(size=14), text_color=("#E0E1FA", "#E0E1FA"),
        ).pack(pady=(6, 28))

        for line in ("Patients, doctors & appointments in one place",
                     "Billing, pharmacy stock & analytics built in",
                     "Role-based access for your whole team"):
            row = ctk.CTkFrame(wrapper, fg_color="transparent")
            row.pack(anchor="w", pady=4, fill="x")
            ctk.CTkLabel(row, text="✓", font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=config.COLOR_ACCENT, width=20).pack(side="left")
            ctk.CTkLabel(row, text=line, font=ctk.CTkFont(size=13),
                         text_color=("#E9EAFB", "#E9EAFB")).pack(side="left")

        ctk.CTkLabel(
            panel, text=f"v{config.APP_VERSION}",
            font=ctk.CTkFont(size=11), text_color=("#B9BCF0", "#B9BCF0"),
        ).place(relx=0.06, rely=0.96, anchor="w")

    def _build_form_panel(self) -> None:
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        card = ctk.CTkFrame(right, width=360, corner_radius=16, fg_color=("white", "gray17"))
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Welcome back", font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, pady=(38, 2), padx=36, sticky="w")

        ctk.CTkLabel(
            card, text="Sign in to continue to your dashboard.", font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
        ).grid(row=1, column=0, pady=(0, 24), padx=36, sticky="w")

        ctk.CTkLabel(card, text="Username", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("gray30", "gray70")).grid(row=2, column=0, padx=36, sticky="w")
        self.username_entry = ctk.CTkEntry(card, placeholder_text="e.g. admin2", width=288, height=38)
        self.username_entry.grid(row=3, column=0, padx=36, pady=(4, 14))
        self.username_entry.focus_set()

        ctk.CTkLabel(card, text="Password", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("gray30", "gray70")).grid(row=4, column=0, padx=36, sticky="w")

        pw_row = ctk.CTkFrame(card, fg_color="transparent", width=288, height=38)
        pw_row.grid(row=5, column=0, padx=36, pady=(4, 4))
        pw_row.grid_propagate(False)
        self.password_entry = ctk.CTkEntry(pw_row, placeholder_text="Your password", show="•", width=288, height=38)
        self.password_entry.place(x=0, y=0)
        self.password_entry.bind("<Return>", lambda _e: self._attempt_login())
        self._toggle_btn = ctk.CTkButton(
            pw_row, text="Show", width=52, height=30, corner_radius=6,
            fg_color="transparent", hover_color=("gray85", "gray30"),
            text_color=("gray35", "gray70"), font=ctk.CTkFont(size=11),
            command=self._toggle_password_visibility,
        )
        self._toggle_btn.place(x=228, y=4)

        self.error_label = ctk.CTkLabel(
            card, text="", text_color=config.COLOR_DANGER, font=ctk.CTkFont(size=12),
            wraplength=288, justify="left",
        )
        self.error_label.grid(row=6, column=0, padx=36, pady=(6, 0), sticky="w")

        self.login_button = ctk.CTkButton(
            card, text="Sign In", width=288, height=42,
            fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_PRIMARY_HOVER,
            command=self._attempt_login, font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.login_button.grid(row=7, column=0, padx=36, pady=(14, 8))

        hint = ctk.CTkFrame(card, corner_radius=8, fg_color=config.COLOR_PRIMARY_SOFT)
        hint.grid(row=8, column=0, padx=36, pady=(6, 28), sticky="ew")
        ctk.CTkLabel(
            hint, text="First time here? Default admin login is\nadmin / Admin@123 — change it after signing in.",
            font=ctk.CTkFont(size=11), text_color=(config.COLOR_PRIMARY, "#C7C9FA"),
            justify="left",
        ).pack(padx=10, pady=8, anchor="w")

    # ------------------------------------------------------------------
    def _toggle_password_visibility(self) -> None:
        self._show_password = not self._show_password
        self.password_entry.configure(show="" if self._show_password else "•")
        self._toggle_btn.configure(text="Hide" if self._show_password else "Show")

    def _attempt_login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        self.error_label.configure(text="")

        if not username or not password:
            self.error_label.configure(text="Please enter both username and password.")
            return

        self.login_button.configure(state="disabled", text="Signing in...")
        self.update_idletasks()
        try:
            user = UserController.authenticate(username, password)
        except AuthenticationError as exc:
            self.error_label.configure(text=str(exc))
            logger.info("Login failed for '%s'", username)
        else:
            self._on_login_success(user)
        finally:
            if self.login_button.winfo_exists():
                self.login_button.configure(state="normal", text="Sign In")

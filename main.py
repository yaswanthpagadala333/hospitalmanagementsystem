#!/usr/bin/env python3
"""
main.py
=======
Entry point for the MediCore Hospital Management System.

Responsibilities:
  * Configure CustomTkinter appearance from persisted settings.
  * Ensure the database and a default admin account exist.
  * Show the login screen, then swap in the main application shell on
    successful authentication (and back again on logout).

Run with:
    python main.py
"""

from __future__ import annotations

import sys
import traceback

import customtkinter as ctk

from config import config
from controllers.user_controller import UserController
from models.user import User
from utils.logger import get_logger

logger = get_logger(__name__)


class HospitalManagementApp(ctk.CTk):
    """Root Tk window. Holds exactly one active child frame at a time:
    either the ``LoginView`` or the ``MainWindow``."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.geometry(f"{config.WINDOW_MIN_WIDTH}x{config.WINDOW_MIN_HEIGHT}")
        self.minsize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        try:
            self.state("zoomed")   # start maximised on Windows/Linux where supported
        except Exception:
            pass

        self._current_frame: ctk.CTkFrame | None = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.show_login()

    # ------------------------------------------------------------------
    def _swap_frame(self, frame: ctk.CTkFrame) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

    def show_login(self) -> None:
        from views.login_view import LoginView
        self._swap_frame(LoginView(self, on_login_success=self._handle_login_success))

    def _handle_login_success(self, user: User) -> None:
        from views.main_window import MainWindow
        logger.info("Entering main application shell for user '%s'", user.username)
        self._swap_frame(MainWindow(self, user=user, on_logout=self._handle_logout))

    def _handle_logout(self) -> None:
        logger.info("User logged out; returning to login screen")
        self.show_login()

    def _on_close(self) -> None:
        logger.info("Application closing")
        self.destroy()


def _install_global_exception_hook() -> None:
    """Log uncaught exceptions instead of letting them silently crash the
    Tk mainloop with only a console traceback the user never sees."""

    def _hook(exc_type, exc_value, exc_tb):
        logger.critical("Uncaught exception:\n%s", "".join(
            traceback.format_exception(exc_type, exc_value, exc_tb)
        ))
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def main() -> None:
    _install_global_exception_hook()
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)

    # First-run bootstrap: guarantees there is always a way to log in.
    UserController.ensure_default_admin()

    ctk.set_appearance_mode(config.settings.appearance_mode)
    ctk.set_default_color_theme(config.settings.color_theme)

    app = HospitalManagementApp()
    app.mainloop()

    logger.info("Application closed cleanly")


if __name__ == "__main__":
    main()

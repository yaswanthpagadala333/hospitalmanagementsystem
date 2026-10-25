"""
config.py
=========
Central, single-source-of-truth configuration for the Hospital Management
System. Every other module reads paths, constants and runtime settings
from here instead of hard-coding them, so the application can be
reconfigured (or relocated) by editing exactly one file.

Design notes
------------
* All filesystem paths are resolved relative to the project root using
  ``pathlib.Path`` so the application behaves the same regardless of the
  current working directory it is launched from.
* ``AppConfig`` is a lightweight, importable namespace rather than a class
  that needs to be instantiated — configuration is process-wide constant
  data, so a singleton-by-module pattern is the simplest correct design.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict

# --------------------------------------------------------------------------
# Project directory layout
# --------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent

DATABASE_DIR: Path = BASE_DIR / "database"
DATABASE_PATH: Path = DATABASE_DIR / "hospital.db"
SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"

LOGS_DIR: Path = BASE_DIR / "logs"
EXPORTS_DIR: Path = BASE_DIR / "exports"
REPORTS_DIR: Path = EXPORTS_DIR / "reports"
CSV_EXPORT_DIR: Path = EXPORTS_DIR / "csv"
JSON_EXPORT_DIR: Path = EXPORTS_DIR / "json"
CHARTS_EXPORT_DIR: Path = EXPORTS_DIR / "charts"

ASSETS_DIR: Path = BASE_DIR / "assets"
ICONS_DIR: Path = ASSETS_DIR / "icons"
IMAGES_DIR: Path = ASSETS_DIR / "images"
THEMES_DIR: Path = ASSETS_DIR / "themes"

SETTINGS_FILE: Path = Path(__file__).resolve().parent / "settings.json"

# Ensure runtime directories exist as soon as the config module is imported.
for _directory in (
    LOGS_DIR, EXPORTS_DIR, REPORTS_DIR, CSV_EXPORT_DIR,
    JSON_EXPORT_DIR, CHARTS_EXPORT_DIR, ICONS_DIR, IMAGES_DIR, THEMES_DIR,
):
    _directory.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Application constants
# --------------------------------------------------------------------------
APP_NAME = "MediCore Hospital Management System"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "MediCore General Hospital"

# CustomTkinter appearance
CTK_APPEARANCE_MODE = "System"      # "System" | "Dark" | "Light"
CTK_COLOR_THEME = "blue"            # "blue" | "green" | "dark-blue"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 720

# --------------------------------------------------------------------------
# Shared brand palette. Every screen pulls its accent colours from here
# instead of hard-coding hex values, so the whole app reads as one
# consistent product and the palette can be restyled in a single place.
# --------------------------------------------------------------------------
COLOR_PRIMARY = "#4338CA"        # indigo — brand / primary actions
COLOR_PRIMARY_HOVER = "#3730A3"
COLOR_PRIMARY_SOFT = ("#EEF0FF", "#241F5C")   # light/dark tint for backgrounds
COLOR_ACCENT = "#0EA5A4"         # teal — secondary accent (icons, highlights)
COLOR_SUCCESS = "#16A34A"
COLOR_WARNING = "#D97706"
COLOR_DANGER = "#DC2626"
COLOR_DANGER_HOVER = "#B91C1C"
COLOR_INFO = "#2563EB"
ROLE_BADGE_COLORS = {
    "Admin": "#7C3AED",
    "Doctor": "#0EA5A4",
    "Receptionist": "#2563EB",
    "Pharmacist": "#D97706",
}

# Business rules
DEFAULT_TAX_PERCENT = 5.0
LOW_STOCK_THRESHOLD_DEFAULT = 20
APPOINTMENT_SLOT_MINUTES = 30
CLINIC_OPEN_HOUR = 9
CLINIC_CLOSE_HOUR = 18

# User roles recognised by the access-control layer
ROLE_ADMIN = "Admin"
ROLE_DOCTOR = "Doctor"
ROLE_RECEPTIONIST = "Receptionist"
ROLE_PHARMACIST = "Pharmacist"
ALL_ROLES = (ROLE_ADMIN, ROLE_DOCTOR, ROLE_RECEPTIONIST, ROLE_PHARMACIST)

# Logging
LOG_FILE = LOGS_DIR / "hospital.log"
LOG_MAX_BYTES = 2_000_000
LOG_BACKUP_COUNT = 5

# Networking (used by the scraping module)
HTTP_TIMEOUT_SECONDS = 8
HTTP_USER_AGENT = f"{APP_NAME}/{APP_VERSION} (educational hospital-management project)"


@dataclass
class RuntimeSettings:
    """
    Mutable, user-adjustable settings that are persisted to
    ``config/settings.json``. Separate from the constants above, which are
    developer-level and not meant to change between runs.
    """
    appearance_mode: str = CTK_APPEARANCE_MODE
    color_theme: str = CTK_COLOR_THEME
    low_stock_threshold: int = LOW_STOCK_THRESHOLD_DEFAULT
    tax_percent: float = DEFAULT_TAX_PERCENT
    hospital_name: str = ORGANIZATION_NAME
    currency_symbol: str = "$"

    @classmethod
    def load(cls) -> "RuntimeSettings":
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return cls(**{**asdict(cls()), **data})
            except (json.JSONDecodeError, TypeError):
                pass
        settings = cls()
        settings.save()
        return settings

    def save(self) -> None:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), indent=4), encoding="utf-8"
        )


settings = RuntimeSettings.load()

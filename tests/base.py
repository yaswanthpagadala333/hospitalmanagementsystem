"""
base.py
=======
Shared test infrastructure: ``DatabaseTestCase`` points every controller
/ analytics module's ``db`` reference at a fresh temporary SQLite
database for the duration of one test, then restores the real one
afterwards. This lets integration tests exercise real SQL (not mocks)
without ever touching the application's actual ``hospital.db``.

Note on implementation: controllers do ``from database.database import
db`` at import time, which binds their own module-level ``db`` name to
whatever ``Database`` object was current *at first import*. Patching
``database.database.db`` alone would not affect those already-bound
names, so this helper explicitly (re-)imports every module known to
hold such a binding and overwrites its ``db`` attribute directly —
always relative to the one true original captured when this file is
first loaded, so restoration is correct no matter what order tests run in.
"""

from __future__ import annotations

import importlib
import tempfile
import unittest
from pathlib import Path

from config import config
from database.database import Database
import database.database as _database_module

# The single real ``Database`` instance the application would use. Captured
# once, at import time, so every test restores to the exact same reference
# regardless of what earlier tests did.
_REAL_DB = _database_module.db

# Every module that does ``from database.database import db`` at import
# time and therefore needs to be explicitly re-pointed at the test database.
_PATCHED_MODULE_NAMES = (
    "controllers.patient_controller",
    "controllers.doctor_controller",
    "controllers.appointment_controller",
    "controllers.medicine_controller",
    "controllers.billing_controller",
    "controllers.user_controller",
    "analytics.analytics_engine",
)


class DatabaseTestCase(unittest.TestCase):
    """Base class that gives each test its own throwaway SQLite database."""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_hospital.db"
        self.db = Database(db_path=db_path, schema_path=config.SCHEMA_PATH)

        _database_module.db = self.db
        self._patched_modules = []
        for name in _PATCHED_MODULE_NAMES:
            module = importlib.import_module(name)
            setattr(module, "db", self.db)
            self._patched_modules.append(module)

    def tearDown(self) -> None:
        self.db.close()
        _database_module.db = _REAL_DB
        for module in self._patched_modules:
            setattr(module, "db", _REAL_DB)
        self._tmp_dir.cleanup()

"""
logger.py
=========
Centralised logging configuration. Every module obtains its logger via
``get_logger(__name__)`` so log records are attributable to the module
that produced them, while all handlers (rotating file + console) are
configured exactly once for the whole application.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import config

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("hms")
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (``hms.<name>``) with handlers configured."""
    _configure_root()
    short_name = name.split(".")[-1]
    return logging.getLogger(f"hms.{short_name}")

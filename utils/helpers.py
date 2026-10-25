"""
helpers.py
==========
Small, generically-useful functions that don't belong to any single
model or controller: ID/code generation, currency formatting, and a
lightweight background-task runner that keeps the CustomTkinter GUI
responsive while I/O-bound work (HTTP requests, PDF generation) happens
on a worker thread.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any, Callable

from config import config


def generate_code(prefix: str, sequence_number: int, width: int = 5) -> str:
    """Build a human-readable business code such as ``PAT00042`` or ``DOC00007``."""
    return f"{prefix}{sequence_number:0{width}d}"


def generate_bill_number() -> str:
    """Unique, sortable bill number, e.g. ``INV-20260806-A1B2C3``."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique = uuid.uuid4().hex[:6].upper()
    return f"INV-{stamp}-{unique}"


def format_currency(amount: float) -> str:
    symbol = config.settings.currency_symbol
    return f"{symbol}{amount:,.2f}"


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class BackgroundTask:
    """
    Runs a blocking callable on a daemon thread and marshals the result
    (or exception) back to the caller via callbacks. CustomTkinter is not
    thread-safe for widget mutation, so callbacks scheduled through
    ``widget.after(0, ...)`` by the caller are the safe way to update the
    UI once work finishes — this class only handles the threading part.
    """

    def __init__(
        self,
        target: Callable[..., Any],
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.target = target
        self.on_success = on_success
        self.on_error = on_error
        self._thread: threading.Thread | None = None

    def start(self, *args: Any, **kwargs: Any) -> None:
        def _run() -> None:
            try:
                result = self.target(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - deliberately broad: surface to UI
                if self.on_error:
                    self.on_error(exc)
                return
            if self.on_success:
                self.on_success(result)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

"""
database.py
===========
Thread-safe SQLite access layer for the Hospital Management System.

Why a dedicated module instead of calling ``sqlite3`` directly everywhere?
  * A single place enforces ``PRAGMA foreign_keys = ON`` and row factories.
  * SQLite connections are not safe to share across threads by default;
    the GUI runs background work (e.g. web scraping, PDF export) on
    worker threads (see ``utils.threading_utils``), so each thread gets
    its own connection via ``threading.local``.
  * Centralised error handling + logging for every query.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Sequence

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Raised for any recoverable database-layer failure."""


class Database:
    """
    Thread-safe SQLite wrapper providing connection management,
    schema initialisation, and small query helpers used throughout the
    controller layer.

    A new physical ``sqlite3.Connection`` is created per thread (stored in
    ``threading.local``) and reused for the lifetime of that thread.
    """

    def __init__(self, db_path: Path = config.DATABASE_PATH, schema_path: Path = config.SCHEMA_PATH) -> None:
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._schema_ready = False
        # Schema initialisation is deferred until the database is actually
        # used (see ``connection``) rather than done here in __init__, so
        # that merely *importing* this module — which instantiates the
        # module-level ``db`` singleton below — never touches disk. This
        # matters for tests, which import this module and then immediately
        # redirect ``db`` to a temporary database before any query runs.

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    @property
    def connection(self) -> sqlite3.Connection:
        """Return (creating if necessary) the connection for the current thread."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=True, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn = conn
        if not self._schema_ready:
            self._initialize_schema(conn)
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager giving commit-on-success / rollback-on-error semantics."""
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        with self._init_lock:
            if self._schema_ready:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.schema_path.exists():
                raise DatabaseError(f"Schema file not found: {self.schema_path}")
            script = self.schema_path.read_text(encoding="utf-8")
            try:
                conn.executescript(script)
                conn.commit()
                logger.info("Database schema verified/initialised at %s", self.db_path)
                self._schema_ready = True
            except sqlite3.Error as exc:
                logger.exception("Failed to initialise schema")
                raise DatabaseError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def execute(self, query: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE statement and commit. Returns the cursor
        (use ``cursor.lastrowid`` / ``cursor.rowcount`` as needed)."""
        try:
            with self.transaction() as conn:
                cursor = conn.execute(query, params)
                return cursor
        except sqlite3.IntegrityError as exc:
            logger.warning("Integrity error running query %s | params=%s | %s", query, params, exc)
            raise DatabaseError(f"Data integrity error: {exc}") from exc
        except sqlite3.Error as exc:
            logger.exception("Database error running query: %s", query)
            raise DatabaseError(str(exc)) from exc

    def executemany(self, query: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        try:
            with self.transaction() as conn:
                return conn.executemany(query, seq_of_params)
        except sqlite3.Error as exc:
            logger.exception("Database error running executemany: %s", query)
            raise DatabaseError(str(exc)) from exc

    def fetch_one(self, query: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        try:
            cursor = self.connection.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as exc:
            logger.exception("Database error running fetch_one: %s", query)
            raise DatabaseError(str(exc)) from exc

    def fetch_all(self, query: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        try:
            cursor = self.connection.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as exc:
            logger.exception("Database error running fetch_all: %s", query)
            raise DatabaseError(str(exc)) from exc


# A process-wide default instance. Controllers import this rather than
# constructing their own ``Database`` object, keeping a single physical
# database file per running application while still giving every thread
# its own connection under the hood.
db = Database()

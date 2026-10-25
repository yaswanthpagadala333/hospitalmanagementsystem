"""
exporter.py
===========
Generic CSV / JSON export (and CSV import) helpers used by every module
that needs to hand data to the outside world — patient lists, billing
history, analytics tables, etc. Kept independent of any specific model so
it can serialise plain dictionaries or dataclasses uniformly.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def _to_dict(record: Any) -> dict:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return record
    raise TypeError(f"Cannot export object of type {type(record)!r}; expected dict or dataclass")


def _timestamped_name(prefix: str, extension: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}.{extension}"


def export_to_csv(records: Sequence[Any], prefix: str, fieldnames: Sequence[str] | None = None) -> Path:
    """Write ``records`` (dicts or dataclasses) to a timestamped CSV file
    inside ``exports/csv`` and return the resulting path."""
    rows = [_to_dict(r) for r in records]
    if not rows:
        raise ValueError("Nothing to export: record list is empty")

    fieldnames = list(fieldnames) if fieldnames else list(rows[0].keys())
    out_path = config.CSV_EXPORT_DIR / _timestamped_name(prefix, "csv")

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    logger.info("Exported %d records to CSV: %s", len(rows), out_path)
    return out_path


def export_to_json(records: Sequence[Any] | dict, prefix: str) -> Path:
    """Write ``records`` to a timestamped, pretty-printed JSON file inside
    ``exports/json`` and return the resulting path."""
    if isinstance(records, dict):
        payload: Any = records
    else:
        payload = [_to_dict(r) for r in records]

    out_path = config.JSON_EXPORT_DIR / _timestamped_name(prefix, "json")
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    count = len(payload) if isinstance(payload, list) else 1
    logger.info("Exported %d record(s) to JSON: %s", count, out_path)
    return out_path


def import_from_csv(path: Path) -> list[dict]:
    """Read a CSV file into a list of plain dictionaries."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [dict(row) for row in reader]
    logger.info("Imported %d rows from CSV: %s", len(rows), path)
    return rows


def import_from_json(path: Path) -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info("Imported JSON data from: %s", path)
    return data

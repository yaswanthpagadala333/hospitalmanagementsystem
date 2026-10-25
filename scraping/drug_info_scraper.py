"""
drug_info_scraper.py
=====================
Fetches public reference information about a medicine from Wikipedia
(drug names generally have a stable "drugbox" infobox there) so
pharmacy staff can quickly look up drug class / usage information from
inside the app without leaving it. This demonstrates ``requests`` +
``BeautifulSoup`` + ``re`` working together, with disk caching and a
threaded, non-blocking API for the GUI layer.

Design notes
------------
* Network calls never run on the GUI thread — ``fetch_async`` wraps the
  blocking ``fetch`` call in a ``BackgroundTask`` (see ``utils.helpers``).
* Results are cached to ``exports/json/drug_cache.json`` for a
  configurable TTL, so repeated lookups (and offline demos) don't require
  a fresh network round-trip every time.
* All parsing is defensive: Wikipedia's markup can vary page to page, so
  missing sections are treated as "unknown" rather than raising.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from config import config
from utils.helpers import BackgroundTask
from utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_PATH: Path = config.JSON_EXPORT_DIR / "drug_info_cache.json"
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week
_WIKIPEDIA_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_WIKIPEDIA_PAGE_URL = "https://en.wikipedia.org/wiki/{title}"

# Matches parenthetical citation markers like "[12]" so they can be stripped
# out of scraped prose before it's shown to the user.
_CITATION_MARKER_RE = re.compile(r"\[\d+\]")
# Collapses runs of whitespace produced by stripping tags out of HTML.
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class DrugInfo:
    query: str
    title: str
    summary: str
    drug_class: Optional[str]
    source_url: str
    fetched_at: float
    from_cache: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class DrugInfoScraper:
    """Looks up general reference information about a medicine name."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.HTTP_USER_AGENT})

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------
    @staticmethod
    def _load_cache() -> dict:
        if _CACHE_PATH.exists():
            try:
                return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Drug info cache was corrupt; starting fresh.")
        return {}

    @staticmethod
    def _save_cache(cache: dict) -> None:
        _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def _get_cached(self, key: str) -> Optional[DrugInfo]:
        cache = self._load_cache()
        entry = cache.get(key.lower())
        if not entry:
            return None
        if time.time() - entry.get("fetched_at", 0) > _CACHE_TTL_SECONDS:
            return None
        info = DrugInfo(**entry)
        info.from_cache = True
        return info

    def _store_cache(self, key: str, info: DrugInfo) -> None:
        cache = self._load_cache()
        cache[key.lower()] = info.to_dict()
        self._save_cache(cache)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_text(text: str) -> str:
        text = _CITATION_MARKER_RE.sub("", text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    def _extract_drug_class(self, html: str) -> Optional[str]:
        """Best-effort extraction of the 'Drug class' row from Wikipedia's
        infobox using BeautifulSoup + a regex label match, since infobox
        row labels vary in wording ('Drug class', 'Class', etc.)."""
        soup = BeautifulSoup(html, "lxml")
        label_pattern = re.compile(r"drug\s*class|^class$", re.IGNORECASE)

        for row in soup.select("table.infobox tr"):
            header_cell = row.find(["th", "td"])
            if header_cell and label_pattern.search(header_cell.get_text(strip=True)):
                value_cell = row.find_all(["td"])
                if value_cell:
                    return self._clean_text(value_cell[-1].get_text(" ", strip=True))
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch(self, drug_name: str, use_cache: bool = True) -> DrugInfo:
        """Blocking lookup — call from a worker thread (see ``fetch_async``)."""
        drug_name = drug_name.strip()
        if not drug_name:
            raise ValueError("Drug name cannot be empty.")

        if use_cache:
            cached = self._get_cached(drug_name)
            if cached:
                logger.info("Drug info cache hit for '%s'", drug_name)
                return cached

        title = quote(drug_name.replace(" ", "_"))
        summary_url = _WIKIPEDIA_SUMMARY_API.format(title=title)

        try:
            resp = self._session.get(summary_url, timeout=config.HTTP_TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Drug info lookup failed for '%s': %s", drug_name, exc)
            raise ConnectionError(f"Could not reach the reference server: {exc}") from exc

        payload = resp.json()
        if payload.get("type") == "disambiguation" or "extract" not in payload:
            raise LookupError(f"No clear reference page found for '{drug_name}'.")

        resolved_title = payload.get("title", drug_name)
        summary_text = self._clean_text(payload.get("extract", ""))
        page_url = payload.get("content_urls", {}).get("desktop", {}).get(
            "page", _WIKIPEDIA_PAGE_URL.format(title=title)
        )

        drug_class = None
        try:
            page_resp = self._session.get(page_url, timeout=config.HTTP_TIMEOUT_SECONDS)
            page_resp.raise_for_status()
            drug_class = self._extract_drug_class(page_resp.text)
        except requests.RequestException as exc:
            logger.info("Could not fetch full page for drug-class extraction: %s", exc)

        info = DrugInfo(
            query=drug_name,
            title=resolved_title,
            summary=summary_text or "No summary available.",
            drug_class=drug_class,
            source_url=page_url,
            fetched_at=time.time(),
        )
        self._store_cache(drug_name, info)
        logger.info("Fetched drug info for '%s' -> '%s'", drug_name, resolved_title)
        return info

    def fetch_async(self, drug_name: str, on_success, on_error, use_cache: bool = True) -> BackgroundTask:
        """Non-blocking version for use from the GUI: runs ``fetch`` on a
        daemon thread and invokes ``on_success(DrugInfo)`` or
        ``on_error(Exception)`` when done."""
        task = BackgroundTask(target=self.fetch, on_success=on_success, on_error=on_error)
        task.start(drug_name, use_cache)
        return task

"""
validators.py
=============
Regex-driven input validation shared by models and views. Keeping every
pattern in one module means the same validation rule is used both for the
GUI's inline feedback and the model layer's integrity checks, so the two
can never silently drift apart.
"""

from __future__ import annotations

import re
from datetime import date, datetime

# --------------------------------------------------------------------
# Compiled regular expressions
# --------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# Accepts formats like: +1 555-123-4567 | 9876543210 | (021) 555-0100
PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,17}$")

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{1,49}$")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")            # YYYY-MM-DD
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")       # HH:MM 24-hour

LICENSE_RE = re.compile(r"^[A-Z]{2,4}-\d{4,8}$")          # e.g. MED-20394

CODE_RE = re.compile(r"^[A-Z]{2,4}\d{3,8}$")               # generated internal codes

STRONG_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$"
)

VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


class ValidationError(ValueError):
    """Raised by validators when a value fails validation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def is_valid_email(value: str) -> bool:
    return bool(value) and bool(EMAIL_RE.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    if not value:
        return False
    digits_only = re.sub(r"\D", "", value)
    return bool(PHONE_RE.match(value.strip())) and 7 <= len(digits_only) <= 15


def is_valid_name(value: str) -> bool:
    return bool(value) and bool(NAME_RE.match(value.strip()))


def is_valid_date(value: str) -> bool:
    if not value or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_time(value: str) -> bool:
    return bool(value) and bool(TIME_RE.match(value.strip()))


def is_past_or_today(value: str) -> bool:
    """Used for date-of-birth style fields."""
    return is_valid_date(value) and datetime.strptime(value, "%Y-%m-%d").date() <= date.today()


def is_future_or_today(value: str) -> bool:
    """Used for appointment / expiry date style fields."""
    return is_valid_date(value) and datetime.strptime(value, "%Y-%m-%d").date() >= date.today()


def is_valid_blood_group(value: str) -> bool:
    return value in VALID_BLOOD_GROUPS


def is_valid_license(value: str) -> bool:
    return bool(value) and bool(LICENSE_RE.match(value.strip().upper()))


def is_strong_password(value: str) -> bool:
    return bool(value) and bool(STRONG_PASSWORD_RE.match(value))


def sanitize_search_term(value: str) -> str:
    """Strip characters that have no place in a plain-text search box,
    while allowing normal punctuation used in names/addresses."""
    return re.sub(r"[^\w\s@.\-,'#/]", "", value or "").strip()


def calculate_age(date_of_birth: str) -> int:
    """Compute age in whole years from an ISO date-of-birth string."""
    dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    today = date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years

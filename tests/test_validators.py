"""
test_validators.py
===================
Unit tests for the regex-based validation helpers. These are pure
functions with no database dependency, so they run fast and in
isolation from everything else.
"""

from __future__ import annotations

import unittest

from utils import validators


class TestEmailValidation(unittest.TestCase):

    def test_accepts_valid_emails(self) -> None:
        for email in ("john@example.com", "j.doe+test@sub.example.co.uk", "a@b.io"):
            with self.subTest(email=email):
                self.assertTrue(validators.is_valid_email(email))

    def test_rejects_invalid_emails(self) -> None:
        for email in ("not-an-email", "missing@domain", "@nodomain.com", "", None):
            with self.subTest(email=email):
                self.assertFalse(validators.is_valid_email(email))


class TestPhoneValidation(unittest.TestCase):

    def test_accepts_valid_phone_numbers(self) -> None:
        for phone in ("555-234-9988", "+1 555 123 4567", "(021) 555-0100", "9876543210"):
            with self.subTest(phone=phone):
                self.assertTrue(validators.is_valid_phone(phone))

    def test_rejects_invalid_phone_numbers(self) -> None:
        for phone in ("123", "not a phone", "", None):
            with self.subTest(phone=phone):
                self.assertFalse(validators.is_valid_phone(phone))


class TestDateValidation(unittest.TestCase):

    def test_accepts_valid_iso_dates(self) -> None:
        self.assertTrue(validators.is_valid_date("2026-08-08"))
        self.assertTrue(validators.is_valid_date("1999-01-01"))

    def test_rejects_malformed_dates(self) -> None:
        for value in ("08-08-2026", "2026/08/08", "2026-13-40", "not a date", ""):
            with self.subTest(value=value):
                self.assertFalse(validators.is_valid_date(value))

    def test_past_or_today(self) -> None:
        self.assertTrue(validators.is_past_or_today("1990-01-01"))
        self.assertFalse(validators.is_past_or_today("2099-01-01"))

    def test_future_or_today(self) -> None:
        self.assertTrue(validators.is_future_or_today("2099-01-01"))
        self.assertFalse(validators.is_future_or_today("1990-01-01"))


class TestAgeCalculation(unittest.TestCase):

    def test_calculates_age_correctly(self) -> None:
        # Fixed, unambiguous historical date so the test never depends on "today".
        from datetime import date
        dob = "2000-01-01"
        expected = date.today().year - 2000
        if (date.today().month, date.today().day) < (1, 1):
            expected -= 1  # pragma: no cover - Jan 1 edge case, never true here
        self.assertEqual(validators.calculate_age(dob), expected)


class TestMiscValidators(unittest.TestCase):

    def test_blood_group_validation(self) -> None:
        self.assertTrue(validators.is_valid_blood_group("O+"))
        self.assertTrue(validators.is_valid_blood_group("AB-"))
        self.assertFalse(validators.is_valid_blood_group("Z+"))

    def test_license_validation(self) -> None:
        self.assertTrue(validators.is_valid_license("MED-20394"))
        self.assertFalse(validators.is_valid_license("MED20394"))
        self.assertFalse(validators.is_valid_license(""))

    def test_strong_password(self) -> None:
        self.assertTrue(validators.is_strong_password("Admin@123"))
        self.assertFalse(validators.is_strong_password("weak"))
        self.assertFalse(validators.is_strong_password("nouppercase1@"))
        self.assertFalse(validators.is_strong_password("NOLOWERCASE1@"))
        self.assertFalse(validators.is_strong_password("NoDigits@@"))
        self.assertFalse(validators.is_strong_password("NoSymbols123"))

    def test_sanitize_search_term_strips_dangerous_characters(self) -> None:
        self.assertEqual(validators.sanitize_search_term("O'Brien; DROP TABLE"), "O'Brien DROP TABLE")
        self.assertEqual(validators.sanitize_search_term("  jane@example.com  "), "jane@example.com")


if __name__ == "__main__":
    unittest.main()

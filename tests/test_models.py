"""
test_models.py
===============
Unit tests for the domain model layer (validation rules, computed
properties). No database required — models are plain dataclasses.
"""

from __future__ import annotations

import unittest

from models.billing import Bill, BillItem
from models.doctor import Doctor
from models.medicine import Medicine
from models.patient import Patient
from utils.validators import ValidationError


class TestPatientModel(unittest.TestCase):

    def _make_patient(self, **overrides) -> Patient:
        defaults = dict(
            first_name="Jane", last_name="Roe", date_of_birth="1985-03-20",
            gender="Female", phone="555-234-9988", email="jane@example.com", blood_group="A+",
        )
        defaults.update(overrides)
        return Patient(**defaults)

    def test_valid_patient_passes_validation(self) -> None:
        patient = self._make_patient()
        patient.validate()  # should not raise

    def test_full_name_property(self) -> None:
        self.assertEqual(self._make_patient().full_name, "Jane Roe")

    def test_age_property_computes_correctly(self) -> None:
        patient = self._make_patient(date_of_birth="2000-01-01")
        self.assertGreaterEqual(patient.age, 25)

    def test_rejects_invalid_date_of_birth(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(date_of_birth="not-a-date").validate()

    def test_rejects_future_date_of_birth(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(date_of_birth="2099-01-01").validate()

    def test_rejects_invalid_gender(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(gender="Unknown").validate()

    def test_rejects_invalid_phone(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(phone="abc").validate()

    def test_rejects_invalid_email_when_provided(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(email="not-an-email").validate()

    def test_allows_missing_optional_email(self) -> None:
        patient = self._make_patient(email=None)
        patient.validate()  # should not raise

    def test_rejects_invalid_blood_group(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_patient(blood_group="Z+").validate()


class TestDoctorModel(unittest.TestCase):

    def _make_doctor(self, **overrides) -> Doctor:
        defaults = dict(
            first_name="Greg", last_name="House", specialization="Diagnostics",
            department="Diagnostics", phone="555-777-1212", license_number="MED-99887",
            consultation_fee=150,
        )
        defaults.update(overrides)
        return Doctor(**defaults)

    def test_valid_doctor_passes_validation(self) -> None:
        self._make_doctor().validate()

    def test_full_name_has_title_prefix(self) -> None:
        self.assertEqual(self._make_doctor().full_name, "Dr. Greg House")

    def test_rejects_malformed_license(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_doctor(license_number="INVALID").validate()

    def test_rejects_negative_fee(self) -> None:
        with self.assertRaises(ValidationError):
            self._make_doctor(consultation_fee=-10).validate()

    def test_availability_list_parses_csv(self) -> None:
        doctor = self._make_doctor(availability_days="Mon,Wed,Fri")
        self.assertEqual(doctor.availability_list, ["Mon", "Wed", "Fri"])


class TestMedicineModel(unittest.TestCase):

    def test_low_stock_detection(self) -> None:
        med = Medicine(name="Amoxicillin", category="Antibiotic", unit_price=2.5,
                        stock_quantity=5, reorder_level=20)
        self.assertTrue(med.is_low_stock)

    def test_not_low_stock_when_above_reorder_level(self) -> None:
        med = Medicine(name="Paracetamol", category="Analgesic", unit_price=0.5,
                        stock_quantity=300, reorder_level=50)
        self.assertFalse(med.is_low_stock)

    def test_rejects_negative_price(self) -> None:
        med = Medicine(name="Test", category="Test", unit_price=-1)
        with self.assertRaises(ValidationError):
            med.validate()

    def test_expired_detection(self) -> None:
        med = Medicine(name="Old Drug", category="Test", unit_price=1.0, expiry_date="2000-01-01")
        self.assertTrue(med.is_expired)
        med2 = Medicine(name="Fresh Drug", category="Test", unit_price=1.0, expiry_date="2099-01-01")
        self.assertFalse(med2.is_expired)


class TestBillingModel(unittest.TestCase):

    def test_bill_item_computes_amount_automatically(self) -> None:
        item = BillItem(description="Paracetamol", item_type="Medicine", quantity=10, unit_price=0.5)
        self.assertEqual(item.amount, 5.0)

    def test_bill_totals_computed_correctly(self) -> None:
        items = [
            BillItem(description="Consultation", item_type="Consultation", quantity=1, unit_price=150),
            BillItem(description="Amoxicillin", item_type="Medicine", quantity=10, unit_price=2.5),
        ]
        bill = Bill(patient_id=1, items=items, tax_percent=5, discount_amount=10)
        self.assertEqual(bill.subtotal, 175.0)
        self.assertEqual(bill.tax_amount, 8.75)
        self.assertEqual(bill.total_amount, 173.75)  # 175 + 8.75 - 10

    def test_bill_requires_at_least_one_item(self) -> None:
        bill = Bill(patient_id=1, items=[])
        with self.assertRaises(ValidationError):
            bill.validate()

    def test_bill_item_rejects_zero_quantity(self) -> None:
        item = BillItem(description="X", item_type="Other", quantity=0, unit_price=1.0)
        with self.assertRaises(ValidationError):
            item.validate()


if __name__ == "__main__":
    unittest.main()

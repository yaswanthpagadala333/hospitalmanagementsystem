"""
test_controllers.py
====================
Integration tests for the controller layer, run against a fresh
temporary SQLite database per test (see ``tests.base.DatabaseTestCase``).
These exercise real SQL and real business rules — appointment conflict
detection, atomic bill creation, stock deduction limits, authentication
— rather than mocking the database away.
"""

from __future__ import annotations

import unittest

from tests.base import DatabaseTestCase


class TestPatientController(DatabaseTestCase):

    def test_create_and_fetch_patient(self) -> None:
        from controllers.patient_controller import PatientController
        from models.patient import Patient

        patient = PatientController.create(Patient(
            first_name="Jane", last_name="Roe", date_of_birth="1985-03-20",
            gender="Female", phone="555-234-9988",
        ))
        self.assertIsNotNone(patient.id)
        self.assertEqual(patient.patient_code, "PAT00001")

        fetched = PatientController.get_by_id(patient.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.full_name, "Jane Roe")

    def test_search_finds_by_partial_name(self) -> None:
        from controllers.patient_controller import PatientController
        from models.patient import Patient

        PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                          date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        PatientController.create(Patient(first_name="John", last_name="Smith",
                                          date_of_birth="1978-11-02", gender="Male", phone="555-321-7788"))

        results = PatientController.search("Roe")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].first_name, "Jane")

    def test_deactivate_hides_from_active_list(self) -> None:
        from controllers.patient_controller import PatientController
        from models.patient import Patient

        patient = PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                                     date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        self.assertEqual(len(PatientController.list_all()), 1)
        PatientController.deactivate(patient.id)
        self.assertEqual(len(PatientController.list_all()), 0)
        self.assertEqual(len(PatientController.list_all(include_inactive=True)), 1)


class TestAppointmentController(DatabaseTestCase):

    def _seed_patient_and_doctor(self):
        from controllers.patient_controller import PatientController
        from controllers.doctor_controller import DoctorController
        from models.patient import Patient
        from models.doctor import Doctor

        patient = PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                                     date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        doctor = DoctorController.create(Doctor(first_name="Greg", last_name="House",
                                                 specialization="Diagnostics", department="Diagnostics",
                                                 phone="555-777-1212", license_number="MED-99887"))
        return patient, doctor

    def test_book_appointment_succeeds(self) -> None:
        from controllers.appointment_controller import AppointmentController
        from models.appointment import Appointment

        patient, doctor = self._seed_patient_and_doctor()
        appt = AppointmentController.book(Appointment(
            patient_id=patient.id, doctor_id=doctor.id,
            appointment_date="2026-08-10", appointment_time="10:30",
        ))
        self.assertIsNotNone(appt.id)
        self.assertEqual(appt.status, "Scheduled")

    def test_double_booking_same_slot_is_rejected(self) -> None:
        from controllers.appointment_controller import AppointmentController
        from models.appointment import Appointment
        from utils.validators import ValidationError

        patient, doctor = self._seed_patient_and_doctor()
        AppointmentController.book(Appointment(
            patient_id=patient.id, doctor_id=doctor.id,
            appointment_date="2026-08-10", appointment_time="10:30",
        ))
        with self.assertRaises(ValidationError):
            AppointmentController.book(Appointment(
                patient_id=patient.id, doctor_id=doctor.id,
                appointment_date="2026-08-10", appointment_time="10:30",
            ))

    def test_booking_outside_clinic_hours_is_rejected(self) -> None:
        from controllers.appointment_controller import AppointmentController
        from models.appointment import Appointment
        from utils.validators import ValidationError

        patient, doctor = self._seed_patient_and_doctor()
        with self.assertRaises(ValidationError):
            AppointmentController.book(Appointment(
                patient_id=patient.id, doctor_id=doctor.id,
                appointment_date="2026-08-10", appointment_time="22:00",
            ))

    def test_status_update_persists(self) -> None:
        from controllers.appointment_controller import AppointmentController
        from models.appointment import Appointment

        patient, doctor = self._seed_patient_and_doctor()
        appt = AppointmentController.book(Appointment(
            patient_id=patient.id, doctor_id=doctor.id,
            appointment_date="2026-08-10", appointment_time="10:30",
        ))
        AppointmentController.update_status(appt.id, "Completed", diagnosis="Stable")
        fetched = AppointmentController.get_by_id(appt.id)
        self.assertEqual(fetched.status, "Completed")
        self.assertEqual(fetched.diagnosis, "Stable")


class TestMedicineController(DatabaseTestCase):

    def test_adjust_stock_increases_and_decreases(self) -> None:
        from controllers.medicine_controller import MedicineController
        from models.medicine import Medicine

        med = MedicineController.create(Medicine(name="Amoxicillin", category="Antibiotic",
                                                   unit_price=2.5, stock_quantity=15, reorder_level=20))
        MedicineController.adjust_stock(med.id, 50, "restock")
        self.assertEqual(MedicineController.get_by_id(med.id).stock_quantity, 65)

        MedicineController.adjust_stock(med.id, -10, "dispensed")
        self.assertEqual(MedicineController.get_by_id(med.id).stock_quantity, 55)

    def test_adjust_stock_rejects_going_negative(self) -> None:
        from controllers.medicine_controller import MedicineController
        from models.medicine import Medicine
        from utils.validators import ValidationError

        med = MedicineController.create(Medicine(name="Amoxicillin", category="Antibiotic",
                                                   unit_price=2.5, stock_quantity=5, reorder_level=20))
        with self.assertRaises(ValidationError):
            MedicineController.adjust_stock(med.id, -10, "over-dispense")

    def test_low_stock_items_reported_correctly(self) -> None:
        from controllers.medicine_controller import MedicineController
        from models.medicine import Medicine

        MedicineController.create(Medicine(name="Low Stock Drug", category="Test",
                                            unit_price=1.0, stock_quantity=5, reorder_level=20))
        MedicineController.create(Medicine(name="Well Stocked Drug", category="Test",
                                            unit_price=1.0, stock_quantity=500, reorder_level=20))
        low = MedicineController.low_stock_items()
        self.assertEqual(len(low), 1)
        self.assertEqual(low[0].name, "Low Stock Drug")


class TestBillingController(DatabaseTestCase):

    def test_create_bill_atomically_persists_items(self) -> None:
        from controllers.patient_controller import PatientController
        from controllers.billing_controller import BillingController
        from models.patient import Patient
        from models.billing import Bill, BillItem

        patient = PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                                     date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        bill = BillingController.create_bill(Bill(patient_id=patient.id, items=[
            BillItem(description="Consultation", item_type="Consultation", quantity=1, unit_price=150),
            BillItem(description="Amoxicillin", item_type="Medicine", quantity=10, unit_price=2.5),
        ], tax_percent=5))

        self.assertIsNotNone(bill.id)
        fetched = BillingController.get_by_id(bill.id)
        self.assertEqual(len(fetched.items), 2)
        self.assertEqual(fetched.total_amount, 183.75)

    def test_record_payment_updates_status(self) -> None:
        from controllers.patient_controller import PatientController
        from controllers.billing_controller import BillingController
        from models.patient import Patient
        from models.billing import Bill, BillItem

        patient = PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                                     date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        bill = BillingController.create_bill(Bill(patient_id=patient.id, items=[
            BillItem(description="Consultation", item_type="Consultation", quantity=1, unit_price=100),
        ]))
        BillingController.record_payment(bill.id, "Paid", "Cash")
        fetched = BillingController.get_by_id(bill.id)
        self.assertEqual(fetched.payment_status, "Paid")
        self.assertEqual(fetched.payment_method, "Cash")

    def test_total_revenue_only_counts_paid_bills(self) -> None:
        from controllers.patient_controller import PatientController
        from controllers.billing_controller import BillingController
        from models.patient import Patient
        from models.billing import Bill, BillItem

        patient = PatientController.create(Patient(first_name="Jane", last_name="Roe",
                                                     date_of_birth="1985-03-20", gender="Female", phone="555-234-9988"))
        paid_bill = BillingController.create_bill(Bill(patient_id=patient.id, tax_percent=0, items=[
            BillItem(description="A", item_type="Consultation", quantity=1, unit_price=100)]))
        BillingController.create_bill(Bill(patient_id=patient.id, tax_percent=0, items=[
            BillItem(description="B", item_type="Consultation", quantity=1, unit_price=200)]))
        BillingController.record_payment(paid_bill.id, "Paid", "Cash")

        self.assertEqual(BillingController.total_revenue(), 100.0)
        self.assertEqual(BillingController.total_outstanding(), 200.0)


class TestUserController(DatabaseTestCase):

    def test_default_admin_can_log_in(self) -> None:
        from controllers.user_controller import UserController

        UserController.ensure_default_admin()
        user = UserController.authenticate("admin", "Admin@123")
        self.assertEqual(user.role, "Admin")

    def test_wrong_password_is_rejected(self) -> None:
        from controllers.user_controller import UserController, AuthenticationError

        UserController.ensure_default_admin()
        with self.assertRaises(AuthenticationError):
            UserController.authenticate("admin", "WrongPassword123!")

    def test_deactivated_user_cannot_log_in(self) -> None:
        from controllers.user_controller import UserController, AuthenticationError

        UserController.ensure_default_admin()
        admin = UserController.authenticate("admin", "Admin@123")
        UserController.deactivate(admin.id)
        with self.assertRaises(AuthenticationError):
            UserController.authenticate("admin", "Admin@123")

    def test_passwords_are_never_stored_in_plaintext(self) -> None:
        from controllers.user_controller import UserController
        from models.user import User

        user = UserController.create_user(
            User(username="drwatson", full_name="Dr. Watson", role="Doctor"), "SecurePass1!",
        )
        self.assertNotEqual(user.password_hash, "SecurePass1!")
        self.assertGreater(len(user.password_hash), 20)


if __name__ == "__main__":
    unittest.main()

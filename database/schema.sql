-- =====================================================================
--  Hospital Management System — SQLite Schema
--  Enforces referential integrity, sensible defaults and CHECK
--  constraints so invalid data is rejected at the database layer,
--  not only in the Python application layer.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- USERS (system accounts / staff logins, role-based access control)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('Admin', 'Doctor', 'Receptionist', 'Pharmacist')),
    full_name       TEXT NOT NULL,
    email           TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_login      TEXT
);

-- ---------------------------------------------------------------------
-- PATIENTS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code            TEXT NOT NULL UNIQUE,
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    date_of_birth           TEXT NOT NULL,
    gender                  TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
    phone                   TEXT NOT NULL,
    email                   TEXT,
    address                 TEXT,
    blood_group             TEXT CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-', NULL)),
    emergency_contact_name  TEXT,
    emergency_contact_phone TEXT,
    allergies               TEXT,
    is_active               INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients (last_name, first_name);

-- ---------------------------------------------------------------------
-- DOCTORS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_code         TEXT NOT NULL UNIQUE,
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    specialization      TEXT NOT NULL,
    department          TEXT NOT NULL,
    phone               TEXT NOT NULL,
    email               TEXT,
    license_number      TEXT NOT NULL UNIQUE,
    consultation_fee    REAL NOT NULL DEFAULT 0 CHECK (consultation_fee >= 0),
    years_experience    INTEGER NOT NULL DEFAULT 0 CHECK (years_experience >= 0),
    availability_days   TEXT NOT NULL DEFAULT 'Mon,Tue,Wed,Thu,Fri',
    is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- APPOINTMENTS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          INTEGER NOT NULL REFERENCES patients (id) ON DELETE CASCADE,
    doctor_id           INTEGER NOT NULL REFERENCES doctors (id) ON DELETE RESTRICT,
    appointment_date    TEXT NOT NULL,          -- ISO date  YYYY-MM-DD
    appointment_time    TEXT NOT NULL,          -- 24h time HH:MM
    status              TEXT NOT NULL DEFAULT 'Scheduled'
                        CHECK (status IN ('Scheduled', 'Completed', 'Cancelled', 'No-Show')),
    reason              TEXT,
    diagnosis           TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (doctor_id, appointment_date, appointment_time)
);
CREATE INDEX IF NOT EXISTS idx_appt_date ON appointments (appointment_date);
CREATE INDEX IF NOT EXISTS idx_appt_patient ON appointments (patient_id);
CREATE INDEX IF NOT EXISTS idx_appt_doctor ON appointments (doctor_id);

-- ---------------------------------------------------------------------
-- MEDICINES (pharmacy inventory)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_code       TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,
    manufacturer        TEXT,
    unit_price          REAL NOT NULL CHECK (unit_price >= 0),
    stock_quantity      INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    reorder_level       INTEGER NOT NULL DEFAULT 20 CHECK (reorder_level >= 0),
    batch_number        TEXT,
    expiry_date         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_medicine_name ON medicines (name);

-- ---------------------------------------------------------------------
-- PRESCRIPTIONS (medicines prescribed during an appointment)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id      INTEGER NOT NULL REFERENCES appointments (id) ON DELETE CASCADE,
    medicine_id         INTEGER NOT NULL REFERENCES medicines (id) ON DELETE RESTRICT,
    dosage              TEXT NOT NULL,
    frequency           TEXT NOT NULL,
    duration_days       INTEGER NOT NULL CHECK (duration_days > 0),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- BILLS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_number         TEXT NOT NULL UNIQUE,
    patient_id          INTEGER NOT NULL REFERENCES patients (id) ON DELETE RESTRICT,
    appointment_id      INTEGER REFERENCES appointments (id) ON DELETE SET NULL,
    bill_date           TEXT NOT NULL DEFAULT (datetime('now')),
    subtotal            REAL NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    tax_percent         REAL NOT NULL DEFAULT 0 CHECK (tax_percent >= 0),
    tax_amount          REAL NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    discount_amount     REAL NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    total_amount        REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    payment_status      TEXT NOT NULL DEFAULT 'Unpaid' CHECK (payment_status IN ('Unpaid', 'Paid', 'Partially Paid', 'Refunded')),
    payment_method      TEXT CHECK (payment_method IN ('Cash', 'Card', 'Insurance', 'Online', NULL)),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bills_patient ON bills (patient_id);

-- ---------------------------------------------------------------------
-- BILL ITEMS (line items of a bill: consultation, medicines, tests...)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bill_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id             INTEGER NOT NULL REFERENCES bills (id) ON DELETE CASCADE,
    description         TEXT NOT NULL,
    item_type           TEXT NOT NULL CHECK (item_type IN ('Consultation', 'Medicine', 'Test', 'Procedure', 'Other')),
    quantity            INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price          REAL NOT NULL CHECK (unit_price >= 0),
    amount              REAL NOT NULL CHECK (amount >= 0)
);

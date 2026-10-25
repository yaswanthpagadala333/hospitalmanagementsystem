# MediCore — Hospital Management System

A complete, desktop Hospital Management System built in Python: patient and
doctor records, appointment scheduling with conflict detection, pharmacy
inventory, billing with PDF invoices, an analytics dashboard, and a
threaded drug-information lookup — all behind a role-aware CustomTkinter
GUI backed by SQLite.

This was built as a full application, not a toy demo: every feature listed
below is implemented and was exercised end-to-end (automated tests plus
manual GUI walkthroughs) while building it, not just written and assumed
to work.

---

## Features

| Module | What it does |
|---|---|
| **Authentication** | Role-based login (Admin / Doctor / Receptionist / Pharmacist), PBKDF2-hashed passwords, per-role sidebar visibility. |
| **Patients** | Full CRUD, search, soft-delete (deactivate), CSV/JSON export. |
| **Doctors** | Full CRUD, search by name/specialization/department, CSV export. |
| **Appointments** | Booking with live conflict detection and clinic-hours validation, status workflow (Scheduled → Completed/Cancelled/No-Show), diagnosis & notes. |
| **Billing** | Multi-item invoices built atomically, payment tracking, one-click PDF invoice generation. |
| **Pharmacy** | Inventory CRUD, stock adjustment with negative-stock protection, low-stock & expiry alerts, threaded Wikipedia drug-info lookup. |
| **Analytics** | KPI dashboard, revenue statistics (mean/median/std/percentiles via NumPy), 8 charts (Matplotlib/Seaborn) covering revenue trends, demographics, department load, inventory, etc. |
| **Reports** | Patient medical summary PDFs (ReportLab), bulk CSV/JSON export of every table. |

---

## Tech Stack

- **Python 3.13+**
- **SQLite** — file-based relational storage, no server required
- **CustomTkinter** — the desktop GUI
- **pandas / NumPy** — analytics computation
- **Matplotlib / Seaborn** — charts, embedded live in the GUI
- **BeautifulSoup4 / Requests** — drug-information web lookup
- **ReportLab** — PDF invoices, prescriptions, and reports
- **Pillow** — image handling
- **Regex, threading, logging, csv, json** — standard library, used throughout

---

## Architecture

The codebase follows a layered / clean architecture so each piece can be
understood, tested, and changed independently:

```
main.py            Entry point — wires the login screen to the main window
config/             App-wide constants and persisted user settings
database/           SQLite connection manager + schema (thread-safe)
models/             Plain dataclasses: validation + (de)serialization only
controllers/        Business logic — the only layer that talks to the DB
views/               CustomTkinter screens (one per feature) + shared widgets
reports/             ReportLab PDF generation
analytics/           pandas/NumPy stats + Matplotlib/Seaborn charts
scraping/            BeautifulSoup/requests drug-info lookup (threaded)
utils/               Validators, security (hashing), logging, CSV/JSON export
tests/               unittest suite — model, validator, and controller tests
```

**Data flow:** a View never touches SQL directly — it calls a Controller,
which validates a Model and persists it through the shared `Database`
wrapper. This means the business rules (e.g. "a doctor can't be double
booked", "stock can't go negative") live in exactly one place and are
enforced no matter which screen — or test — triggers them.

---

## Getting Started

### 1. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> CustomTkinter needs Tk. On most Windows/macOS Python installs this is
> already bundled. On Linux, if you see `ModuleNotFoundError: No module
> named 'tkinter'`, install it via your package manager first, e.g.
> `sudo apt install python3-tk`.

### 3. Run it

```bash
python main.py
```

On first launch the app creates `database/hospital.db` from
`database/schema.sql` automatically and seeds one administrator account:

```
Username: admin
Password: Admin@123
```

(Change this password after first login in a real deployment —
`UserController.change_password` is there for exactly that.)

---

## Running the Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers regex validators, model validation rules, and
controller-level integration tests (booking conflicts, atomic bill
creation, stock limits, authentication) against a **temporary, isolated
SQLite database** — tests never read or write your real `hospital.db`.

---

## Project Structure

```
HospitalManagementSystem/
│
├── assets/                 icons / images / theme files
├── database/
│   ├── database.py         thread-safe SQLite connection manager
│   ├── hospital.db         created on first run (not committed)
│   └── schema.sql          table definitions, constraints, indexes
├── models/                 Patient, Doctor, Appointment, Medicine, Billing, User
├── controllers/             business logic per resource + auth
├── views/                   one file per screen + views/widgets/ (shared components)
├── reports/                 PDF generation (ReportLab)
├── analytics/               pandas/NumPy stats + Matplotlib/Seaborn charts
├── scraping/                 threaded Wikipedia drug-info lookup
├── utils/                    validators, security, logging, CSV/JSON export, helpers
├── exports/                  generated CSV / JSON / PDF / chart output (not committed)
├── logs/                     rotating application log (not committed)
├── config/                   config.py (constants) + settings.json (persisted, not committed)
├── tests/                    unittest suite
├── main.py
├── requirements.txt
└── README.md
```

---

## Design Notes Worth Knowing

- **Thread safety:** SQLite connections aren't safe to share across
  threads, so `Database` keeps one connection per thread
  (`threading.local`). The drug-info lookup runs on a background thread
  (`utils.helpers.BackgroundTask`) so a slow network call never freezes
  the UI.
- **Validation lives in the model, enforced by the controller:** every
  model has a `.validate()` that raises `ValidationError` with a
  human-readable message — the same message a form dialog shows inline.
- **Soft deletes:** patients and doctors are deactivated, never hard
  deleted, so appointment and billing history stays intact.
- **Atomic billing:** a bill and all of its line items are written in a
  single SQLite transaction — either the whole invoice saves, or none of
  it does.
- **Passwords** are never stored in plaintext: PBKDF2-HMAC-SHA256 with a
  per-user random salt and 260,000 iterations.

---

## A note on academic use

If you're using this for coursework, make sure submitting AI-assisted
code fits your course's academic integrity policy, and take the time to
actually read through the code — you should be able to explain any part
of it. The comments and this README are written with that in mind.
"# hospitalmanagementsystem" 

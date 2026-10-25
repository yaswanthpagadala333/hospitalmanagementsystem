"""
tests package
=============
Unit and integration tests for the Hospital Management System, built on
the standard library's ``unittest``. Run the whole suite with:

    python -m unittest discover -s tests -v

Every test that touches the database points ``database.database.db`` at
a throwaway SQLite file (see ``tests.base.DatabaseTestCase``) so tests
never read or write the real ``hospital.db`` used by the running app.
"""

"""
user_controller.py
===================
Business logic for authentication and staff-account management. Passwords
are never stored or compared in plaintext (see ``utils.security``).
"""

from __future__ import annotations

from typing import Optional

from database.database import db
from models.user import User
from utils.helpers import now_iso
from utils.logger import get_logger
from utils.security import generate_salt, hash_password, verify_password
from utils.validators import require, is_strong_password

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when login credentials are invalid or the account is inactive."""


class UserController:

    @staticmethod
    def create_user(user: User, plain_password: str) -> User:
        user.validate()
        require(is_strong_password(plain_password),
                "Password must be 8+ characters and include upper/lowercase, a digit and a symbol.")
        existing = db.fetch_one("SELECT id FROM users WHERE username = ?", (user.username,))
        require(existing is None, f"Username '{user.username}' is already taken.")

        salt = generate_salt()
        password_hash = hash_password(plain_password, salt)
        cursor = db.execute(
            """
            INSERT INTO users (username, password_hash, salt, role, full_name, email, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user.username, password_hash, salt, user.role, user.full_name, user.email, int(user.is_active)),
        )
        user.id = cursor.lastrowid
        user.password_hash, user.salt = password_hash, salt
        logger.info("Created user account #%s (%s / %s)", user.id, user.username, user.role)
        return user

    @staticmethod
    def authenticate(username: str, plain_password: str) -> User:
        row = db.fetch_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
        if row is None:
            logger.warning("Failed login attempt for unknown username '%s'", username)
            raise AuthenticationError("Invalid username or password.")

        user = User.from_row(row)
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated. Contact an administrator.")
        if not verify_password(plain_password, user.salt, user.password_hash):
            logger.warning("Failed login attempt for user '%s'", username)
            raise AuthenticationError("Invalid username or password.")

        db.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_iso(), user.id))
        logger.info("User '%s' (%s) logged in", user.username, user.role)
        return user

    @staticmethod
    def update(user: User) -> User:
        """Update the editable profile fields (full name, role, email) of
        an existing account. Username and password are changed through
        their own dedicated flows."""
        user.validate()
        cursor_row = db.fetch_one("SELECT id FROM users WHERE id = ?", (user.id,))
        require(cursor_row is not None, "User not found.")
        db.execute(
            "UPDATE users SET full_name = ?, role = ?, email = ? WHERE id = ?",
            (user.full_name, user.role, user.email, user.id),
        )
        logger.info("Updated user account #%s (%s / %s)", user.id, user.username, user.role)
        return user

    @staticmethod
    def change_password(user_id: int, new_password: str) -> None:
        require(is_strong_password(new_password),
                "Password must be 8+ characters and include upper/lowercase, a digit and a symbol.")
        salt = generate_salt()
        password_hash = hash_password(new_password, salt)
        db.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (password_hash, salt, user_id))
        logger.info("Password changed for user #%s", user_id)

    @staticmethod
    def deactivate(user_id: int) -> None:
        row = db.fetch_one("SELECT role FROM users WHERE id = ?", (user_id,))
        if row and row["role"] == "Admin":
            active_admins = db.fetch_one(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'Admin' AND is_active = 1"
            )
            require(active_admins["c"] > 1, "Cannot deactivate the last active administrator.")
        db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))

    @staticmethod
    def reactivate(user_id: int) -> None:
        db.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))

    @staticmethod
    def list_all() -> list[User]:
        rows = db.fetch_all("SELECT * FROM users ORDER BY full_name")
        return [User.from_row(r) for r in rows]

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return User.from_row(row) if row else None

    @staticmethod
    def ensure_default_admin() -> None:
        """Create a first-run administrator account if the users table is
        empty, so the application is never in an un-loginable state."""
        row = db.fetch_one("SELECT COUNT(*) AS c FROM users")
        if row and row["c"] == 0:
            admin = User(username="admin", full_name="System Administrator", role="Admin")
            UserController.create_user(admin, "Admin@123")
            logger.info("Default admin account created (username='admin', password='Admin@123')")

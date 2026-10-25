"""
security.py
============
Password hashing utilities. Uses PBKDF2-HMAC-SHA256 (via the standard
library's ``hashlib``) with a per-user random salt and a high iteration
count — no plaintext or reversibly-encrypted passwords are ever stored.
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ITERATIONS = 260_000
_HASH_ALGORITHM = "sha256"


def generate_salt() -> str:
    """Return a new cryptographically random salt, hex-encoded."""
    return os.urandom(16).hex()


def hash_password(password: str, salt: str) -> str:
    """Derive a hex-encoded PBKDF2 hash for ``password`` using ``salt``."""
    derived = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _ITERATIONS,
    )
    return derived.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time comparison of a supplied password against the stored hash."""
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)

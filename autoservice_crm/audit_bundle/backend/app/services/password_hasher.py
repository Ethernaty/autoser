from __future__ import annotations

from passlib.context import CryptContext


class PasswordHasher:
    """Password hashing service."""

    def __init__(self, scheme: str = "bcrypt"):
        self._context = CryptContext(schemes=[scheme], deprecated="auto")

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._context.verify(password, password_hash)
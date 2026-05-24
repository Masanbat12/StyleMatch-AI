from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

from user_repository import DuplicateUserError, UserRepository

PBKDF2_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 8


class AuthenticationError(ValueError):
    pass


def _normalize_username(username: str) -> str:
    cleaned = username.strip().lower()
    if not cleaned:
        raise AuthenticationError("Username is required.")
    if len(cleaned) < 3:
        raise AuthenticationError("Username must be at least 3 characters long.")
    if not all(character.isalnum() or character in {"_", "-", "."} for character in cleaned):
        raise AuthenticationError("Username may contain letters, numbers, dots, dashes, and underscores only.")
    return cleaned


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthenticationError("Password must be at least 8 characters long.")


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return base64.b64encode(digest).decode("utf-8")


class AuthService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def ensure_indexes(self) -> None:
        self.user_repository.ensure_indexes()

    def register_user(self, username: str, password: str) -> dict[str, Any]:
        normalized_username = _normalize_username(username)
        _validate_password(password)

        salt = os.urandom(16)
        password_hash = _hash_password(password, salt)

        try:
            return self.user_repository.create_user(
                username=normalized_username,
                password_hash=password_hash,
                password_salt=base64.b64encode(salt).decode("utf-8"),
            )
        except DuplicateUserError as exc:
            raise AuthenticationError("That username is already in use.") from exc

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        normalized_username = _normalize_username(username)
        user = self.user_repository.find_by_username(normalized_username)
        if user is None:
            raise AuthenticationError("Incorrect username or password.")

        salt = base64.b64decode(user["password_salt"])
        candidate_hash = _hash_password(password, salt)
        if not hmac.compare_digest(candidate_hash, user["password_hash"]):
            raise AuthenticationError("Incorrect username or password.")

        self.user_repository.update_last_login(user["id"])
        refreshed = self.user_repository.find_by_id(user["id"])
        return refreshed or user

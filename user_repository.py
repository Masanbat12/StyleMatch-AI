from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgres_client import UniqueViolation, ensure_schema, get_connection


class DuplicateUserError(ValueError):
    pass


class UserRepository:
    def __init__(self) -> None:
        ensure_schema()

    def ensure_indexes(self) -> None:
        ensure_schema()

    def find_by_username(self, username: str) -> dict[str, Any] | None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, password_hash, password_salt, created_at, last_login_at
                    FROM users
                    WHERE username = %s
                    """,
                    (username,),
                )
                document = cursor.fetchone()
        return self._serialize_user(document) if document else None

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            numeric_id = int(user_id)
        except (TypeError, ValueError):
            return None

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, password_hash, password_salt, created_at, last_login_at
                    FROM users
                    WHERE id = %s
                    """,
                    (numeric_id,),
                )
                document = cursor.fetchone()
        return self._serialize_user(document) if document else None

    def create_user(
        self,
        username: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (username, password_hash, password_salt, created_at, last_login_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, username, password_hash, password_salt, created_at, last_login_at
                        """,
                        (username, password_hash, password_salt, now, None),
                    )
                    document = cursor.fetchone()
        except UniqueViolation as exc:
            raise DuplicateUserError("duplicate username") from exc
        return self._serialize_user(document)

    def update_last_login(self, user_id: str) -> None:
        try:
            numeric_id = int(user_id)
        except (TypeError, ValueError):
            return

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET last_login_at = %s WHERE id = %s",
                    (datetime.now(UTC), numeric_id),
                )

    def _serialize_user(self, document: dict[str, Any] | None) -> dict[str, Any]:
        if document is None:
            return {}
        serialized = dict(document)
        serialized["id"] = str(serialized["id"])
        return serialized

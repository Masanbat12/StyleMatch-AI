from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgres_client import Jsonb, coerce_account_id, ensure_schema, get_connection


class InteractionRepository:
    def __init__(self) -> None:
        ensure_schema()

    def ensure_indexes(self) -> None:
        ensure_schema()

    def log_event(
        self,
        user_id: str,
        username: str | None,
        action: str,
        profile: dict[str, str],
        outfit: dict[str, Any],
        source: str,
        original_outfit: dict[str, Any] | None = None,
        refined_outfit: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = datetime.now(UTC)
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_feedback (
                        user_id, username, action, profile, outfit, source,
                        original_outfit, refined_outfit, metadata, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        account_id,
                        username,
                        action,
                        Jsonb(profile),
                        Jsonb(outfit),
                        source,
                        Jsonb(original_outfit) if original_outfit is not None else None,
                        Jsonb(refined_outfit) if refined_outfit is not None else None,
                        Jsonb(metadata or {}),
                        created_at,
                    ),
                )
                document = cursor.fetchone()
        payload = dict(document)
        payload["user_id"] = str(payload["user_id"])
        payload["id"] = str(payload["id"])
        return payload

    def get_recent_events(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM user_feedback
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (account_id, limit),
                )
                rows = cursor.fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["user_id"] = str(event["user_id"])
            event["id"] = str(event["id"])
        return events

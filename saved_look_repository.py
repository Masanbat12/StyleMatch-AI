from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgres_client import Jsonb, coerce_account_id, ensure_schema, get_connection


class SavedLookRepository:
    def __init__(self) -> None:
        ensure_schema()

    def ensure_indexes(self) -> None:
        ensure_schema()

    def save_look(
        self,
        user_id: str,
        username: str | None,
        profile: dict[str, str],
        outfit: dict[str, Any],
        source: str,
        explanation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        saved_at = datetime.now(UTC)
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO saved_looks (user_id, username, profile, outfit, source, explanation, metadata, saved_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        account_id,
                        username,
                        Jsonb(profile),
                        Jsonb(outfit),
                        source,
                        explanation,
                        Jsonb(metadata or {}),
                        saved_at,
                    ),
                )
                document = cursor.fetchone()
        payload = dict(document)
        payload["user_id"] = str(payload["user_id"])
        payload["id"] = str(payload["id"])
        return payload

    def get_saved_looks(self, user_id: str) -> list[dict[str, Any]]:
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM saved_looks
                    WHERE user_id = %s
                    ORDER BY saved_at DESC
                    """,
                    (account_id,),
                )
                rows = cursor.fetchall()

        formatted_rows: list[dict[str, Any]] = []
        for raw_row in rows:
            row = dict(raw_row)
            row["id"] = str(row["id"])
            row["user_id"] = str(row["user_id"])
            row["created_at"] = row["saved_at"].astimezone(UTC).isoformat()
            profile = row.get("profile", {})
            outfit = row.get("outfit", {})
            row["skin_tone"] = profile.get("skin_tone")
            row["undertone"] = profile.get("undertone")
            row["style"] = profile.get("style")
            row["occasion"] = profile.get("occasion")
            row["shirt_color"] = outfit.get("shirt_color")
            row["pants_color"] = outfit.get("pants_color")
            row["shoes_color"] = outfit.get("shoes_color")
            row["score"] = outfit.get("score", 0)
            formatted_rows.append(row)

        return formatted_rows

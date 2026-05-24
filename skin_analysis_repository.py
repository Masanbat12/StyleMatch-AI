from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgres_client import Jsonb, coerce_account_id, ensure_schema, get_connection


class SkinAnalysisRepository:
    def __init__(self) -> None:
        ensure_schema()

    def ensure_indexes(self) -> None:
        ensure_schema()

    def add_analysis(self, user_id: str, username: str | None, analysis_result: dict[str, Any]) -> dict[str, Any]:
        analyzed_at = datetime.now(UTC)
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO skin_analysis_history (
                        user_id, username, skin_tone, undertone, confidence, confidence_label, brightness,
                        dominant_skin_hex, sample_pixel_count, quality_flags, warnings, note, analyzed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        account_id,
                        username,
                        analysis_result["skin_tone"],
                        analysis_result["undertone"],
                        analysis_result["confidence"],
                        analysis_result.get("confidence_label"),
                        analysis_result.get("brightness"),
                        analysis_result.get("dominant_skin_hex"),
                        analysis_result.get("sample_pixel_count"),
                        Jsonb(analysis_result.get("quality_flags", [])),
                        Jsonb(analysis_result.get("warnings", [])),
                        analysis_result.get("note"),
                        analyzed_at,
                    ),
                )
                document = cursor.fetchone()
        payload = dict(document)
        payload["user_id"] = str(payload["user_id"])
        payload["id"] = str(payload["id"])
        return payload

    def get_recent_analyses(self, user_id: str, limit: int = 12) -> list[dict[str, Any]]:
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM skin_analysis_history
                    WHERE user_id = %s
                    ORDER BY analyzed_at DESC
                    LIMIT %s
                    """,
                    (account_id, limit),
                )
                rows = cursor.fetchall()
        analyses = [dict(row) for row in rows]
        for analysis in analyses:
            analysis["user_id"] = str(analysis["user_id"])
            analysis["id"] = str(analysis["id"])
        return analyses

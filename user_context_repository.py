from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgres_client import Jsonb, coerce_account_id, ensure_schema, get_connection


def default_user_context(user_id: str, username: str | None = None) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "user_id": user_id,
        "username": username,
        "current_inferred_skin_tone": None,
        "current_inferred_undertone": None,
        "skin_profile_confidence": 0.0,
        "skin_analysis_count": 0,
        "historical_skin_tone_estimates": [],
        "historical_undertone_estimates": [],
        "preferred_color_weights": {},
        "disliked_color_weights": {},
        "slot_color_preferences": {
            "shirt": {},
            "pants": {},
            "shoes": {},
        },
        "preferred_style_weights": {},
        "preferred_occasion_weights": {},
        "interaction_counts": {},
        "confidence_signals": {
            "colors": 0.0,
            "styles": 0.0,
            "occasions": 0.0,
            "skin_profile": 0.0,
        },
        "insights": {
            "top_colors": [],
            "disliked_colors": [],
            "top_styles": [],
            "top_occasions": [],
        },
        "last_updated_at": now,
    }


class UserContextRepository:
    def __init__(self) -> None:
        ensure_schema()

    def ensure_indexes(self) -> None:
        ensure_schema()

    def get_user_context(self, user_id: str, username: str | None = None) -> dict[str, Any]:
        account_id = coerce_account_id(user_id)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM user_preferences WHERE user_id = %s", (account_id,))
                document = cursor.fetchone()
        if document is None:
            return default_user_context(user_id, username=username)
        return dict(document)

    def save_user_context(self, context: dict[str, Any]) -> dict[str, Any]:
        account_id = coerce_account_id(context["user_id"])
        context["last_updated_at"] = datetime.now(UTC)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_preferences (
                        user_id,
                        username,
                        current_inferred_skin_tone,
                        current_inferred_undertone,
                        skin_profile_confidence,
                        skin_analysis_count,
                        historical_skin_tone_estimates,
                        historical_undertone_estimates,
                        preferred_color_weights,
                        disliked_color_weights,
                        slot_color_preferences,
                        preferred_style_weights,
                        preferred_occasion_weights,
                        interaction_counts,
                        confidence_signals,
                        insights,
                        last_updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        current_inferred_skin_tone = EXCLUDED.current_inferred_skin_tone,
                        current_inferred_undertone = EXCLUDED.current_inferred_undertone,
                        skin_profile_confidence = EXCLUDED.skin_profile_confidence,
                        skin_analysis_count = EXCLUDED.skin_analysis_count,
                        historical_skin_tone_estimates = EXCLUDED.historical_skin_tone_estimates,
                        historical_undertone_estimates = EXCLUDED.historical_undertone_estimates,
                        preferred_color_weights = EXCLUDED.preferred_color_weights,
                        disliked_color_weights = EXCLUDED.disliked_color_weights,
                        slot_color_preferences = EXCLUDED.slot_color_preferences,
                        preferred_style_weights = EXCLUDED.preferred_style_weights,
                        preferred_occasion_weights = EXCLUDED.preferred_occasion_weights,
                        interaction_counts = EXCLUDED.interaction_counts,
                        confidence_signals = EXCLUDED.confidence_signals,
                        insights = EXCLUDED.insights,
                        last_updated_at = EXCLUDED.last_updated_at
                    """,
                    (
                        account_id,
                        context.get("username"),
                        context.get("current_inferred_skin_tone"),
                        context.get("current_inferred_undertone"),
                        context.get("skin_profile_confidence", 0.0),
                        context.get("skin_analysis_count", 0),
                        Jsonb(context.get("historical_skin_tone_estimates", [])),
                        Jsonb(context.get("historical_undertone_estimates", [])),
                        Jsonb(context.get("preferred_color_weights", {})),
                        Jsonb(context.get("disliked_color_weights", {})),
                        Jsonb(context.get("slot_color_preferences", {})),
                        Jsonb(context.get("preferred_style_weights", {})),
                        Jsonb(context.get("preferred_occasion_weights", {})),
                        Jsonb(context.get("interaction_counts", {})),
                        Jsonb(context.get("confidence_signals", {})),
                        Jsonb(context.get("insights", {})),
                        context["last_updated_at"],
                    ),
                )
        context["user_id"] = str(account_id)
        return context

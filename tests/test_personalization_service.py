from __future__ import annotations

from datetime import UTC, datetime

from personalization_service import PersonalizationService


class FakeUserContextRepository:
    def __init__(self) -> None:
        self.contexts: dict[str, dict] = {}

    def ensure_indexes(self) -> None:
        return

    def get_user_context(self, user_id: str, username: str | None = None) -> dict:
        return self.contexts.get(
            user_id,
            {
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
                "slot_color_preferences": {"shirt": {}, "pants": {}, "shoes": {}},
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
                "last_updated_at": datetime.now(UTC),
            },
        )

    def save_user_context(self, context: dict) -> dict:
        self.contexts[context["user_id"]] = context
        return context


class FakeInteractionRepository:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def ensure_indexes(self) -> None:
        return

    def log_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class FakeSkinAnalysisRepository:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def ensure_indexes(self) -> None:
        return

    def add_analysis(self, user_id: str, username: str | None, analysis_result: dict) -> dict:
        record = {
            "user_id": user_id,
            "username": username,
            "skin_tone": analysis_result["skin_tone"],
            "undertone": analysis_result["undertone"],
            "confidence": analysis_result["confidence"],
            "analyzed_at": datetime.now(UTC),
        }
        self.records.append(record)
        return record

    def get_recent_analyses(self, user_id: str, limit: int = 12) -> list[dict]:
        return [record for record in self.records if record["user_id"] == user_id][:limit]


class FakeSavedLookRepository:
    def __init__(self) -> None:
        self.looks: list[dict] = []

    def ensure_indexes(self) -> None:
        return

    def save_look(self, **kwargs):
        self.looks.append(kwargs)
        return kwargs

    def get_saved_looks(self, user_id: str) -> list[dict]:
        return [look for look in self.looks if look["user_id"] == user_id]


def build_service() -> PersonalizationService:
    return PersonalizationService(
        user_context_repository=FakeUserContextRepository(),
        interaction_repository=FakeInteractionRepository(),
        skin_analysis_repository=FakeSkinAnalysisRepository(),
        saved_look_repository=FakeSavedLookRepository(),
    )


def test_record_feedback_learns_color_and_slot_preferences():
    service = build_service()

    context = service.record_feedback(
        user_id="demo-user",
        username="demo",
        action="save",
        profile={"skin_tone": "medium", "undertone": "neutral", "style": "elegant", "occasion": "date"},
        outfit={"shirt_color": "navy", "pants_color": "beige", "shoes_color": "black", "score": 90},
        source="generator",
        save_look=True,
    )

    assert context["preferred_color_weights"]["navy"] > 0
    assert context["slot_color_preferences"]["shoes"]["black"] > 0
    assert "navy" in context["insights"]["top_colors"]


def test_manual_edit_penalizes_replaced_color_and_rewards_new_color():
    service = build_service()

    context = service.record_feedback(
        user_id="demo-user",
        username="demo",
        action="manual_edit",
        profile={"skin_tone": "medium", "undertone": "neutral", "style": "casual", "occasion": "daily"},
        outfit={"shirt_color": "white", "pants_color": "black", "shoes_color": "black", "score": 82},
        source="manual_builder",
        original_outfit={"shirt_color": "white", "pants_color": "black", "shoes_color": "white", "score": 79},
        refined_outfit={"shirt_color": "white", "pants_color": "black", "shoes_color": "black", "score": 82},
        save_look=False,
    )

    assert context["slot_color_preferences"]["shoes"]["black"] > 0
    assert context["disliked_color_weights"]["white"] > 0


def test_record_skin_analysis_aggregates_current_profile():
    service = build_service()

    service.record_skin_analysis(
        "demo-user",
        "demo",
        {
            "skin_tone": "medium",
            "undertone": "warm",
            "confidence": 0.82,
        },
    )
    context = service.record_skin_analysis(
        "demo-user",
        "demo",
        {
            "skin_tone": "medium",
            "undertone": "warm",
            "confidence": 0.88,
        },
    )

    assert context["current_inferred_skin_tone"] == "medium"
    assert context["current_inferred_undertone"] == "warm"
    assert context["skin_analysis_count"] == 2

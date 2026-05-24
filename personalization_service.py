from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from interaction_repository import InteractionRepository
from saved_look_repository import SavedLookRepository
from skin_analysis_repository import SkinAnalysisRepository
from user_context_repository import UserContextRepository, default_user_context

ACTION_WEIGHTS = {
    "like": {"color": 1.6, "slot": 1.2, "style": 0.9, "occasion": 0.9},
    "save": {"color": 2.4, "slot": 1.8, "style": 1.2, "occasion": 1.2},
    "dislike": {"disliked": 1.8, "style": -0.35, "occasion": -0.25},
    "refine": {"color": 0.4, "slot": 0.4, "style": 0.5, "occasion": 0.5},
    "manual_edit": {"new_color": 3.0, "new_slot": 3.6, "old_color": 2.4, "style": 1.0, "occasion": 1.0},
}

MAX_HISTORY_ITEMS = 10


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _normalize_weight_map(weight_map: dict[str, float]) -> dict[str, float]:
    normalized = {
        key: round(float(value), 2)
        for key, value in weight_map.items()
        if float(value) > 0.05
    }
    return dict(sorted(normalized.items(), key=lambda item: (-item[1], item[0])))


def _top_keys(weight_map: dict[str, float], limit: int = 3) -> list[str]:
    return [key for key, _ in sorted(weight_map.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _recency_weight(analyzed_at: datetime | None) -> float:
    if analyzed_at is None:
        return 1.0
    age_days = max(0.0, (datetime.now(UTC) - analyzed_at).total_seconds() / 86400)
    return max(0.5, 1.0 - min(age_days / 120.0, 0.5))


class PersonalizationService:
    def __init__(
        self,
        user_context_repository: UserContextRepository | None = None,
        interaction_repository: InteractionRepository | None = None,
        skin_analysis_repository: SkinAnalysisRepository | None = None,
        saved_look_repository: SavedLookRepository | None = None,
    ) -> None:
        self.user_context_repository = user_context_repository or UserContextRepository()
        self.interaction_repository = interaction_repository or InteractionRepository()
        self.skin_analysis_repository = skin_analysis_repository or SkinAnalysisRepository()
        self.saved_look_repository = saved_look_repository or SavedLookRepository()

    def ensure_indexes(self) -> None:
        self.user_context_repository.ensure_indexes()
        self.interaction_repository.ensure_indexes()
        self.skin_analysis_repository.ensure_indexes()
        self.saved_look_repository.ensure_indexes()

    def get_user_context(self, user_id: str, username: str | None = None) -> dict[str, Any]:
        context = self.user_context_repository.get_user_context(user_id, username=username)
        return self._serialize_context(context)

    def get_user_insight_note(self, context: dict[str, Any]) -> str | None:
        top_colors = context.get("insights", {}).get("top_colors", [])
        top_styles = context.get("insights", {}).get("top_styles", [])
        if top_colors and top_styles:
            return f"You often prefer {', '.join(top_colors[:2])} tones in {top_styles[0]} looks."
        if top_colors:
            return f"You often prefer {', '.join(top_colors[:2])} tones."
        return None

    def record_skin_analysis(self, user_id: str, username: str | None, analysis_result: dict[str, Any]) -> dict[str, Any]:
        self.skin_analysis_repository.add_analysis(user_id, username, analysis_result)
        analyses = self.skin_analysis_repository.get_recent_analyses(user_id, limit=MAX_HISTORY_ITEMS)
        context = self.user_context_repository.get_user_context(user_id, username=username)

        tone_weights: dict[str, float] = defaultdict(float)
        undertone_weights: dict[str, float] = defaultdict(float)
        tone_history: list[dict[str, Any]] = []
        undertone_history: list[dict[str, Any]] = []

        for record in analyses:
            weight = float(record.get("confidence", 0.5)) * _recency_weight(record.get("analyzed_at"))
            tone = record.get("skin_tone")
            undertone = record.get("undertone")
            if tone:
                tone_weights[tone] += weight
                tone_history.append(
                    {
                        "value": tone,
                        "confidence": float(record.get("confidence", 0.0)),
                        "analyzed_at": _iso_datetime(record.get("analyzed_at")),
                    }
                )
            if undertone:
                undertone_weights[undertone] += weight
                undertone_history.append(
                    {
                        "value": undertone,
                        "confidence": float(record.get("confidence", 0.0)),
                        "analyzed_at": _iso_datetime(record.get("analyzed_at")),
                    }
                )

        context["current_inferred_skin_tone"] = max(tone_weights, key=tone_weights.get, default=None)
        context["current_inferred_undertone"] = max(undertone_weights, key=undertone_weights.get, default=None)
        context["skin_profile_confidence"] = round(
            max(tone_weights.values(), default=0.0) / max(sum(tone_weights.values()), 1e-6),
            2,
        )
        context["skin_analysis_count"] = len(analyses)
        context["historical_skin_tone_estimates"] = tone_history[:MAX_HISTORY_ITEMS]
        context["historical_undertone_estimates"] = undertone_history[:MAX_HISTORY_ITEMS]
        context["confidence_signals"]["skin_profile"] = min(
            1.0, round(sum(float(record.get("confidence", 0.0)) for record in analyses) / max(len(analyses), 1), 2)
        )

        self._refresh_insights(context)
        self.user_context_repository.save_user_context(context)
        return self._serialize_context(context)

    def record_feedback(
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
        save_look: bool = False,
    ) -> dict[str, Any]:
        self.interaction_repository.log_event(
            user_id=user_id,
            username=username,
            action=action,
            profile=profile,
            outfit=outfit,
            source=source,
            original_outfit=original_outfit,
            refined_outfit=refined_outfit,
            metadata=metadata,
        )

        if save_look:
            self.saved_look_repository.save_look(
                user_id=user_id,
                username=username,
                profile=profile,
                outfit=outfit,
                source=source,
                explanation=outfit.get("explanation"),
                metadata=metadata,
            )

        context = self.user_context_repository.get_user_context(user_id, username=username)
        self._apply_feedback_to_context(context, action, profile, outfit, original_outfit, refined_outfit)
        self._refresh_insights(context)
        self.user_context_repository.save_user_context(context)
        return self._serialize_context(context)

    def get_saved_looks(self, user_id: str) -> list[dict[str, Any]]:
        looks = self.saved_look_repository.get_saved_looks(user_id)
        for look in looks:
            saved_at = look.get("saved_at")
            if isinstance(saved_at, datetime):
                look["created_at"] = _iso_datetime(saved_at)
        return looks

    def get_recent_feedback(self, user_id: str, limit: int = 25) -> list[dict[str, Any]]:
        events = self.interaction_repository.get_recent_events(user_id, limit=limit)
        for event in events:
            if "id" in event:
                event["id"] = str(event["id"])
            if isinstance(event.get("created_at"), datetime):
                event["created_at"] = _iso_datetime(event["created_at"])
        return events

    def get_skin_analysis_history(self, user_id: str, limit: int = 12) -> list[dict[str, Any]]:
        analyses = self.skin_analysis_repository.get_recent_analyses(user_id, limit=limit)
        for analysis in analyses:
            if "id" in analysis:
                analysis["id"] = str(analysis["id"])
            if isinstance(analysis.get("analyzed_at"), datetime):
                analysis["analyzed_at"] = _iso_datetime(analysis["analyzed_at"])
        return analyses

    def _apply_feedback_to_context(
        self,
        context: dict[str, Any],
        action: str,
        profile: dict[str, str],
        outfit: dict[str, Any],
        original_outfit: dict[str, Any] | None,
        refined_outfit: dict[str, Any] | None,
    ) -> None:
        counts = context.setdefault("interaction_counts", {})
        counts[action] = int(counts.get(action, 0)) + 1

        preferred_colors = context.setdefault("preferred_color_weights", {})
        disliked_colors = context.setdefault("disliked_color_weights", {})
        slot_preferences = context.setdefault(
            "slot_color_preferences",
            {"shirt": {}, "pants": {}, "shoes": {}},
        )
        style_weights = context.setdefault("preferred_style_weights", {})
        occasion_weights = context.setdefault("preferred_occasion_weights", {})
        confidence_signals = context.setdefault(
            "confidence_signals",
            {"colors": 0.0, "styles": 0.0, "occasions": 0.0, "skin_profile": 0.0},
        )

        weights = ACTION_WEIGHTS[action]
        style = profile["style"]
        occasion = profile["occasion"]
        style_weights[style] = float(style_weights.get(style, 0.0)) + weights.get("style", 0.0)
        occasion_weights[occasion] = float(occasion_weights.get(occasion, 0.0)) + weights.get("occasion", 0.0)

        slot_mapping = {
            "shirt": outfit["shirt_color"],
            "pants": outfit["pants_color"],
            "shoes": outfit["shoes_color"],
        }

        if action in {"like", "save", "refine"}:
            for slot, color in slot_mapping.items():
                preferred_colors[color] = float(preferred_colors.get(color, 0.0)) + weights.get("color", 0.0)
                slot_preferences[slot][color] = float(slot_preferences[slot].get(color, 0.0)) + weights.get("slot", 0.0)
        elif action == "dislike":
            for _, color in slot_mapping.items():
                disliked_colors[color] = float(disliked_colors.get(color, 0.0)) + weights.get("disliked", 0.0)
        elif action == "manual_edit" and original_outfit and refined_outfit:
            for slot in ("shirt", "pants", "shoes"):
                key = f"{slot}_color"
                old_color = original_outfit[key]
                new_color = refined_outfit[key]
                if old_color == new_color:
                    continue
                preferred_colors[new_color] = float(preferred_colors.get(new_color, 0.0)) + weights.get("new_color", 0.0)
                slot_preferences[slot][new_color] = float(slot_preferences[slot].get(new_color, 0.0)) + weights.get("new_slot", 0.0)
                disliked_colors[old_color] = float(disliked_colors.get(old_color, 0.0)) + weights.get("old_color", 0.0)

        total_events = sum(int(value) for value in counts.values())
        confidence_signals["colors"] = min(1.0, round(total_events / 14.0, 2))
        confidence_signals["styles"] = min(1.0, round(sum(abs(value) for value in style_weights.values()) / 10.0, 2))
        confidence_signals["occasions"] = min(1.0, round(sum(abs(value) for value in occasion_weights.values()) / 10.0, 2))

        context["preferred_color_weights"] = _normalize_weight_map(preferred_colors)
        context["disliked_color_weights"] = _normalize_weight_map(disliked_colors)
        context["preferred_style_weights"] = _normalize_weight_map(style_weights)
        context["preferred_occasion_weights"] = _normalize_weight_map(occasion_weights)
        context["slot_color_preferences"] = {
            slot: _normalize_weight_map(slot_weights)
            for slot, slot_weights in slot_preferences.items()
        }

    def _refresh_insights(self, context: dict[str, Any]) -> None:
        context["insights"] = {
            "top_colors": _top_keys(context.get("preferred_color_weights", {}), limit=3),
            "disliked_colors": _top_keys(context.get("disliked_color_weights", {}), limit=3),
            "top_styles": _top_keys(context.get("preferred_style_weights", {}), limit=2),
            "top_occasions": _top_keys(context.get("preferred_occasion_weights", {}), limit=2),
        }

    def _serialize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        serialized = dict(context)
        if "_id" in serialized:
            serialized["_id"] = str(serialized["_id"])
        if isinstance(serialized.get("last_updated_at"), datetime):
            serialized["last_updated_at"] = _iso_datetime(serialized["last_updated_at"])
        return serialized


def create_guest_context() -> dict[str, Any]:
    return default_user_context(user_id="guest-session", username="Guest")


def apply_guest_skin_analysis(
    context: dict[str, Any],
    history: list[dict[str, Any]],
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    history.insert(
        0,
        {
            "skin_tone": analysis_result["skin_tone"],
            "undertone": analysis_result["undertone"],
            "confidence": analysis_result["confidence"],
            "analyzed_at": datetime.now(UTC),
        },
    )
    trimmed_history = history[:MAX_HISTORY_ITEMS]

    tone_weights: dict[str, float] = defaultdict(float)
    undertone_weights: dict[str, float] = defaultdict(float)
    tone_history: list[dict[str, Any]] = []
    undertone_history: list[dict[str, Any]] = []

    for record in trimmed_history:
        weight = float(record.get("confidence", 0.5)) * _recency_weight(record.get("analyzed_at"))
        tone = record.get("skin_tone")
        undertone = record.get("undertone")
        if tone:
            tone_weights[tone] += weight
            tone_history.append(
                {
                    "value": tone,
                    "confidence": float(record.get("confidence", 0.0)),
                    "analyzed_at": _iso_datetime(record.get("analyzed_at")),
                }
            )
        if undertone:
            undertone_weights[undertone] += weight
            undertone_history.append(
                {
                    "value": undertone,
                    "confidence": float(record.get("confidence", 0.0)),
                    "analyzed_at": _iso_datetime(record.get("analyzed_at")),
                }
            )

    context["current_inferred_skin_tone"] = max(tone_weights, key=tone_weights.get, default=None)
    context["current_inferred_undertone"] = max(undertone_weights, key=undertone_weights.get, default=None)
    context["skin_profile_confidence"] = round(
        max(tone_weights.values(), default=0.0) / max(sum(tone_weights.values()), 1e-6),
        2,
    )
    context["skin_analysis_count"] = len(trimmed_history)
    context["historical_skin_tone_estimates"] = tone_history
    context["historical_undertone_estimates"] = undertone_history
    context["confidence_signals"]["skin_profile"] = min(
        1.0,
        round(sum(float(record.get("confidence", 0.0)) for record in trimmed_history) / max(len(trimmed_history), 1), 2),
    )

    service = PersonalizationService.__new__(PersonalizationService)
    service._refresh_insights(context)
    return context


def apply_guest_feedback(
    context: dict[str, Any],
    action: str,
    profile: dict[str, str],
    outfit: dict[str, Any],
    original_outfit: dict[str, Any] | None = None,
    refined_outfit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    service = PersonalizationService.__new__(PersonalizationService)
    service._apply_feedback_to_context(context, action, profile, outfit, original_outfit, refined_outfit)
    service._refresh_insights(context)
    return context

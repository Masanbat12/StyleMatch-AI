from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models import Outfit, UserProfile
from supabase_client import get_supabase, supabase_is_configured


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "saved_outfits.db"
LIKE_POINTS = 3
UNLIKE_POINTS = -5
FEEDBACK_SLOTS = ("shirt", "pants", "shoes")


logger = logging.getLogger(__name__)


@contextmanager
def _connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _supabase_payload(
    profile: UserProfile,
    outfit: Outfit,
    explanation: str | None,
    source: str,
    user_id: str | None,
    username: str | None,
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "username": username,
        "skin_tone": profile.skin_tone,
        "undertone": profile.undertone,
        "style": profile.style,
        "occasion": profile.occasion,
        "shirt_color": outfit.shirt_color,
        "pants_color": outfit.pants_color,
        "shoes_color": outfit.shoes_color,
        "score": outfit.score,
        "explanation": explanation,
        "source": source,
    }


def active_storage_backend() -> str:
    return "supabase" if supabase_is_configured() else "local"


def init_db() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                skin_tone TEXT NOT NULL,
                undertone TEXT NOT NULL,
                style TEXT NOT NULL,
                occasion TEXT NOT NULL,
                shirt_color TEXT NOT NULL,
                pants_color TEXT NOT NULL,
                shoes_color TEXT NOT NULL,
                score INTEGER NOT NULL,
                explanation TEXT,
                source TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(saved_outfits)").fetchall()
        }
        if "user_id" not in columns:
            connection.execute("ALTER TABLE saved_outfits ADD COLUMN user_id TEXT")
        if "metadata" not in columns:
            connection.execute("ALTER TABLE saved_outfits ADD COLUMN metadata TEXT")
        if "username" not in columns:
            connection.execute("ALTER TABLE saved_outfits ADD COLUMN username TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outfit_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                outfit_key TEXT NOT NULL,
                skin_tone TEXT NOT NULL,
                undertone TEXT NOT NULL,
                style TEXT NOT NULL,
                occasion TEXT NOT NULL,
                shirt_color TEXT NOT NULL,
                pants_color TEXT NOT NULL,
                shoes_color TEXT NOT NULL,
                outfit_score INTEGER NOT NULL,
                feedback TEXT NOT NULL CHECK (feedback IN ('like', 'unlike')),
                points INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'streamlit',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, outfit_key)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outfit_feedback_user_updated_at "
            "ON outfit_feedback(user_id, updated_at DESC)"
        )


def save_outfit(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    score: int,
    user_id: str = "local-user",
    username: str | None = None,
    source: str = "manual_builder",
    explanation: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    metadata_json = json.dumps(metadata or {})

    profile = UserProfile(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
    )
    outfit = Outfit(
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
        score=score,
    )

    if supabase_is_configured() and user_id != "local-user" and not user_id.startswith("guest-"):
        try:
            payload = _supabase_payload(profile, outfit, explanation, source, user_id, username)
            if metadata:
                payload["metadata"] = metadata
            get_supabase().table("saved_outfits").insert(payload).execute()
            return
        except Exception:
            logger.warning("Cloud save failed; saving outfit locally.")

    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO saved_outfits (
                user_id,
                username,
                skin_tone,
                undertone,
                style,
                occasion,
                shirt_color,
                pants_color,
                shoes_color,
                score,
                explanation,
                source,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                profile.skin_tone,
                profile.undertone,
                profile.style,
                profile.occasion,
                outfit.shirt_color,
                outfit.pants_color,
                outfit.shoes_color,
                outfit.score,
                explanation,
                source,
                metadata_json,
            ),
        )


def get_saved_outfits(user_id: str = "local-user") -> list[dict[str, object]]:
    cloud_rows: list[dict[str, object]] = []
    if supabase_is_configured() and user_id != "local-user" and not user_id.startswith("guest-"):
        try:
            response = (
                get_supabase().table("saved_outfits").select("*")
                .eq("user_id", user_id).order("id", desc=True).execute()
            )
            cloud_rows = list(response.data or [])
        except Exception:
            logger.warning("Cloud read failed; showing locally saved outfits.")

    with _connection() as connection:
        rows = connection.execute(
            "SELECT * FROM saved_outfits WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()

    # Local fallback writes remain visible when cloud connectivity recovers.
    outfits = cloud_rows + [dict(row) for row in rows]
    for row in outfits:
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (ValueError, TypeError):
                metadata = {}
        row["metadata"] = metadata if isinstance(metadata, dict) else {}
    return sorted(outfits, key=lambda row: str(row.get("created_at") or ""), reverse=True)


# ---------------------------------------------------------------- like / unlike feedback
def _uses_cloud(user_id: str) -> bool:
    return supabase_is_configured() and user_id != "local-user" and not user_id.startswith("guest-")


def _outfit_key(*parts: str) -> str:
    return "|".join(part.strip().casefold() for part in parts)


def _feedback_points(feedback: str) -> int:
    if feedback == "like":
        return LIKE_POINTS
    if feedback == "unlike":
        return UNLIKE_POINTS
    raise ValueError("Feedback must be either 'like' or 'unlike'.")


def _empty_feedback_context() -> dict[str, Any]:
    return {
        "feedback_count": 0,
        "like_count": 0,
        "unlike_count": 0,
        "color_scores": {},
        "slot_color_scores": {slot: {} for slot in FEEDBACK_SLOTS},
        "style_scores": {},
        "occasion_scores": {},
    }


def _add_score(score_map: dict[str, int], key: str | None, points: int) -> None:
    if key:
        score_map[key] = int(score_map.get(key, 0)) + points


def _feedback_context_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    context = _empty_feedback_context()
    context["feedback_count"] = len(rows)
    for row in rows:
        feedback = str(row.get("feedback") or "")
        points = int(row.get("points") or 0)
        if feedback == "like":
            context["like_count"] += 1
        elif feedback == "unlike":
            context["unlike_count"] += 1
        for slot in FEEDBACK_SLOTS:
            color = row.get(f"{slot}_color")
            color_name = str(color) if color else None
            _add_score(context["color_scores"], color_name, points)
            _add_score(context["slot_color_scores"][slot], color_name, points)
        _add_score(context["style_scores"], str(row.get("style") or ""), points)
        _add_score(context["occasion_scores"], str(row.get("occasion") or ""), points)
    return context


def record_outfit_feedback(
    *,
    user_id: str,
    username: str | None,
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    outfit_score: int,
    feedback: str,
    source: str = "streamlit_feedback",
) -> str:
    """Store one reaction per user and outfit; a new reaction replaces the old one."""
    payload: dict[str, Any] = {
        "user_id": user_id,
        "username": username,
        "outfit_key": _outfit_key(skin_tone, undertone, style, occasion, shirt_color, pants_color, shoes_color),
        "skin_tone": skin_tone,
        "undertone": undertone,
        "style": style,
        "occasion": occasion,
        "shirt_color": shirt_color,
        "pants_color": pants_color,
        "shoes_color": shoes_color,
        "outfit_score": int(outfit_score),
        "feedback": feedback,
        "points": _feedback_points(feedback),
        "source": source,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    if _uses_cloud(user_id):
        try:
            get_supabase().table("outfit_feedback").upsert(payload, on_conflict="user_id,outfit_key").execute()
            return "supabase"
        except Exception:
            logger.warning("Cloud feedback failed; saving the reaction locally.")

    columns = list(payload)
    updates = ", ".join(f"{column} = excluded.{column}" for column in columns if column not in {"user_id", "outfit_key"})
    with _connection() as connection:
        connection.execute(
            f"INSERT INTO outfit_feedback ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)}) "
            f"ON CONFLICT(user_id, outfit_key) DO UPDATE SET {updates}",
            [payload[column] for column in columns],
        )
    return "local"


def get_style_feedback(user_id: str = "local-user") -> dict[str, Any]:
    fields = "feedback, points, style, occasion, shirt_color, pants_color, shoes_color"
    rows: list[dict[str, Any]] | None = None
    if _uses_cloud(user_id):
        try:
            response = (
                get_supabase().table("outfit_feedback").select(fields.replace(" ", ""))
                .eq("user_id", user_id).execute()
            )
            if response.data is not None:
                rows = [dict(row) for row in response.data]
        except Exception:
            logger.warning("Cloud feedback read failed; using local reactions.")
    if rows is None:
        with _connection() as connection:
            local_rows = connection.execute(
                f"SELECT {fields} FROM outfit_feedback WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        rows = [dict(row) for row in local_rows]
    return _feedback_context_from_rows(rows)


def feedback_user_context(feedback: dict[str, Any]) -> dict[str, Any] | None:
    """Translate reactions into the engine's ranking weights (one like = weight 1 per colour).

    Reactions only re-rank suggestions; the engine's score itself stays objective.
    """
    if not feedback.get("feedback_count"):
        return None
    scale = float(LIKE_POINTS)
    colors = feedback.get("color_scores", {})
    return {
        "preferred_color_weights": {c: p / scale for c, p in colors.items() if p > 0},
        "disliked_color_weights": {c: -p / scale for c, p in colors.items() if p < 0},
        "slot_color_preferences": {
            slot: {c: p / scale for c, p in scores.items()}
            for slot, scores in feedback.get("slot_color_scores", {}).items()
        },
    }

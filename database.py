from __future__ import annotations

import sqlite3
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


def _connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


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


def _outfit_key(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
) -> str:
    parts = [
        skin_tone,
        undertone,
        style,
        occasion,
        shirt_color,
        pants_color,
        shoes_color,
    ]
    return "|".join(part.strip().casefold() for part in parts)


def _feedback_points(feedback: str) -> int:
    if feedback == "like":
        return LIKE_POINTS
    if feedback == "unlike":
        return UNLIKE_POINTS
    raise ValueError("Feedback must be either 'like' or 'unlike'.")


def _feedback_payload(
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
    source: str,
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "username": username,
        "outfit_key": _outfit_key(
            skin_tone,
            undertone,
            style,
            occasion,
            shirt_color,
            pants_color,
            shoes_color,
        ),
        "skin_tone": skin_tone,
        "undertone": undertone,
        "style": style,
        "occasion": occasion,
        "shirt_color": shirt_color,
        "pants_color": pants_color,
        "shoes_color": shoes_color,
        "outfit_score": outfit_score,
        "feedback": feedback,
        "points": _feedback_points(feedback),
        "source": source,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _empty_feedback_context() -> dict[str, Any]:
    return {
        "feedback_count": 0,
        "like_count": 0,
        "unlike_count": 0,
        "color_scores": {},
        "slot_color_scores": {
            "shirt": {},
            "pants": {},
            "shoes": {},
        },
        "style_scores": {},
        "occasion_scores": {},
    }


def _add_score(score_map: dict[str, int], key: str | None, points: int) -> None:
    if not key:
        return
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

        colors = {
            "shirt": row.get("shirt_color"),
            "pants": row.get("pants_color"),
            "shoes": row.get("shoes_color"),
        }
        for slot, color in colors.items():
            color_name = str(color) if color else None
            _add_score(context["color_scores"], color_name, points)
            _add_score(context["slot_color_scores"][slot], color_name, points)

        _add_score(context["style_scores"], str(row.get("style") or ""), points)
        _add_score(context["occasion_scores"], str(row.get("occasion") or ""), points)

    return context


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
            """
            CREATE INDEX IF NOT EXISTS idx_outfit_feedback_user_updated_at
            ON outfit_feedback(user_id, updated_at DESC)
            """
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
) -> str:
    del metadata

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

    if supabase_is_configured() and user_id != "local-user":
        try:
            get_supabase().table("saved_outfits").insert(
                _supabase_payload(profile, outfit, explanation, source, user_id, username)
            ).execute()
            return "supabase"
        except Exception:
            pass

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
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
    return "local"


def get_saved_outfits(user_id: str = "local-user") -> list[dict[str, object]]:
    if supabase_is_configured() and user_id != "local-user":
        try:
            query = get_supabase().table("saved_outfits").select("*")
            query = query.eq("user_id", user_id)
            response = query.order("id", desc=True).execute()
            if response.data is not None:
                return list(response.data)
        except Exception:
            pass

    with _connection() as connection:
        if user_id == "local-user":
            rows = connection.execute(
                """
                SELECT
                    id,
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
                    created_at
                FROM saved_outfits
                ORDER BY id DESC
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    id,
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
                    created_at
                FROM saved_outfits
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()

    return [dict(row) for row in rows]


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
    payload = _feedback_payload(
        user_id=user_id,
        username=username,
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
        outfit_score=outfit_score,
        feedback=feedback,
        source=source,
    )

    if supabase_is_configured() and user_id != "local-user":
        try:
            get_supabase().table("outfit_feedback").upsert(
                payload,
                on_conflict="user_id,outfit_key",
            ).execute()
            return "supabase"
        except Exception:
            pass

    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO outfit_feedback (
                user_id,
                username,
                outfit_key,
                skin_tone,
                undertone,
                style,
                occasion,
                shirt_color,
                pants_color,
                shoes_color,
                outfit_score,
                feedback,
                points,
                source,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, outfit_key) DO UPDATE SET
                username = excluded.username,
                skin_tone = excluded.skin_tone,
                undertone = excluded.undertone,
                style = excluded.style,
                occasion = excluded.occasion,
                shirt_color = excluded.shirt_color,
                pants_color = excluded.pants_color,
                shoes_color = excluded.shoes_color,
                outfit_score = excluded.outfit_score,
                feedback = excluded.feedback,
                points = excluded.points,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (
                payload["user_id"],
                payload["username"],
                payload["outfit_key"],
                payload["skin_tone"],
                payload["undertone"],
                payload["style"],
                payload["occasion"],
                payload["shirt_color"],
                payload["pants_color"],
                payload["shoes_color"],
                payload["outfit_score"],
                payload["feedback"],
                payload["points"],
                payload["source"],
                payload["updated_at"],
            ),
        )
    return "local"


def get_style_feedback(user_id: str = "local-user") -> dict[str, Any]:
    rows: list[dict[str, Any]] | None = None

    if supabase_is_configured() and user_id != "local-user":
        try:
            response = (
                get_supabase()
                .table("outfit_feedback")
                .select(
                    "feedback,points,style,occasion,shirt_color,pants_color,shoes_color"
                )
                .eq("user_id", user_id)
                .execute()
            )
            if response.data is not None:
                rows = [dict(row) for row in response.data]
        except Exception:
            rows = None

    if rows is None:
        with _connection() as connection:
            local_rows = connection.execute(
                """
                SELECT feedback, points, style, occasion, shirt_color, pants_color, shoes_color
                FROM outfit_feedback
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        rows = [dict(row) for row in local_rows]

    return _feedback_context_from_rows(rows)

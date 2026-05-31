from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from models import Outfit, UserProfile
from supabase_client import get_supabase, supabase_is_configured


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "saved_outfits.db"


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

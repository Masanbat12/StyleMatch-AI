from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from models import Outfit, UserProfile

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "saved_outfits.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(_connect()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skin_tone TEXT NOT NULL,
                undertone TEXT NOT NULL,
                style TEXT NOT NULL,
                occasion TEXT NOT NULL,
                shirt_color TEXT NOT NULL,
                pants_color TEXT NOT NULL,
                shoes_color TEXT NOT NULL,
                score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in cursor.execute("PRAGMA table_info(outfits)").fetchall()
        }
        if "created_at" not in existing_columns:
            cursor.execute(
                "ALTER TABLE outfits ADD COLUMN created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )

        conn.commit()


def save_outfit(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    score: int,
) -> None:
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

    with closing(_connect()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO outfits (
                skin_tone, undertone, style, occasion,
                shirt_color, pants_color, shoes_color, score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.skin_tone,
                profile.undertone,
                profile.style,
                profile.occasion,
                outfit.shirt_color,
                outfit.pants_color,
                outfit.shoes_color,
                outfit.score,
            ),
        )
        conn.commit()


def get_saved_outfits() -> list[dict[str, object]]:
    with closing(_connect()) as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT id, skin_tone, undertone, style, occasion,
                   shirt_color, pants_color, shoes_color, score, created_at
            FROM outfits
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
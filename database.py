from __future__ import annotations

import sqlite3
from contextlib import closing

DB_NAME = "saved_outfits.db"


def init_db() -> None:
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skin_tone TEXT NOT NULL,
                undertone TEXT NOT NULL,
                style TEXT NOT NULL,
                occasion TEXT NOT NULL,
                shirt_color TEXT NOT NULL,
                pants_color TEXT NOT NULL,
                shoes_color TEXT NOT NULL,
                score INTEGER NOT NULL
            )
            '''
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
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO outfits (
                skin_tone, undertone, style, occasion,
                shirt_color, pants_color, shoes_color, score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (skin_tone, undertone, style, occasion, shirt_color, pants_color, shoes_color, score),
        )
        conn.commit()


def get_saved_outfits():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT id, skin_tone, undertone, style, occasion,
                   shirt_color, pants_color, shoes_color, score
            FROM outfits
            ORDER BY id DESC
            '''
        )
        return cursor.fetchall()

from pathlib import Path

import database


def test_save_and_fetch_outfits(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "saved_outfits.db"

    monkeypatch.setattr(database, "DATA_DIR", data_dir)
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()
    database.save_outfit(
        skin_tone="medium",
        undertone="neutral",
        style="casual",
        occasion="daily",
        shirt_color="white",
        pants_color="black",
        shoes_color="brown",
        score=82,
    )

    outfits = database.get_saved_outfits()

    assert len(outfits) == 1
    assert outfits[0]["shirt_color"] == "white"
    assert outfits[0]["created_at"]

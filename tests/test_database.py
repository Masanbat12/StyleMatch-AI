from __future__ import annotations

from pathlib import Path

import database


def test_local_save_and_fetch_outfits(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "saved_outfits.db"

    monkeypatch.setattr(database, "DATA_DIR", data_dir)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)

    database.init_db()
    backend = database.save_outfit(
        skin_tone="medium",
        undertone="neutral",
        style="casual",
        occasion="daily",
        shirt_color="white",
        pants_color="black",
        shoes_color="brown",
        score=82,
        user_id="demo-user",
        username="messi",
        explanation="Balanced contrast for daily casual wear.",
    )

    outfits = database.get_saved_outfits("demo-user")

    assert backend == "local"
    assert db_path.exists()
    assert len(outfits) == 1
    assert outfits[0]["user_id"] == "demo-user"
    assert outfits[0]["username"] == "messi"
    assert outfits[0]["shirt_color"] == "white"
    assert outfits[0]["explanation"] == "Balanced contrast for daily casual wear."


def test_active_storage_backend_reflects_supabase_configuration(monkeypatch):
    monkeypatch.setattr(database, "supabase_is_configured", lambda: True)
    assert database.active_storage_backend() == "supabase"

    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    assert database.active_storage_backend() == "local"

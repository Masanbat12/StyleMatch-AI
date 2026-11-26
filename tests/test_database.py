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
    database.save_outfit(
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

def _save_for(user_id):
    database.save_outfit("medium", "neutral", "casual", "daily",
                         "white", "black", "brown", 82, user_id=user_id)

def test_local_reads_are_isolated_by_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "looks.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    database.init_db()
    for owner in ("local-user", "account-1", "guest-one", "guest-two"):
        _save_for(owner)
    for owner in ("local-user", "account-1", "guest-one", "guest-two"):
        rows = database.get_saved_outfits(owner)
        assert len(rows) == 1
        assert rows[0]["user_id"] == owner

def test_fallback_saves_remain_visible_after_cloud_recovers(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "looks.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    database.init_db()
    _save_for("account-1")

    class CloudQuery:
        def table(self, *args): return self
        def select(self, *args): return self
        def eq(self, field, value):
            assert (field, value) == ("user_id", "account-1")
            return self
        def order(self, *args, **kwargs): return self
        def execute(self): return SimpleNamespace(data=[{"id": 99, "created_at": "2099-01-01"}])

    monkeypatch.setattr(database, "supabase_is_configured", lambda: True)
    monkeypatch.setattr(database, "get_supabase", lambda: CloudQuery())
    rows = database.get_saved_outfits("account-1")
    assert len(rows) == 2
    assert rows[0]["id"] == 99

def test_guests_do_not_use_cloud_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "looks.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: True)
    def unexpected_cloud_call():
        raise AssertionError("Guest data must remain local")
    monkeypatch.setattr(database, "get_supabase", unexpected_cloud_call)
    database.init_db()
    _save_for("guest-one")
    assert len(database.get_saved_outfits("guest-one")) == 1

def test_saved_avatar_metadata_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "looks.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    database.init_db()
    database.save_outfit("medium", "neutral", "casual", "daily", "white", "black", "brown", 82,
                         user_id="guest-one", metadata={"avatar_model": "female", "shoe_style": "heels"})
    database.init_db()
    row = database.get_saved_outfits("guest-one")[0]
    assert row["metadata"] == {"avatar_model": "female", "shoe_style": "heels"}

def test_new_wardrobe_metadata_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "looks.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    database.init_db()
    selection = {"avatar_model": "female", "top_style": "jacket", "bottom_style": "pants",
                 "shoe_style": "heels", "outerwear_color": "gray"}
    database.save_outfit("medium", "neutral", "casual", "daily", "white", "navy", "white", 82,
                         user_id="guest-one", metadata=selection)
    assert database.get_saved_outfits("guest-one")[0]["metadata"] == selection

def _local_db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(database, "DATA_DIR", data_dir)
    monkeypatch.setattr(database, "DB_PATH", data_dir / "saved_outfits.db")
    monkeypatch.setattr(database, "supabase_is_configured", lambda: False)
    database.init_db()

FEEDBACK_LOOK = dict(
    user_id="demo-user", username="messi", skin_tone="medium", undertone="warm", style="casual",
    occasion="daily", shirt_color="navy", pants_color="beige", shoes_color="white", outfit_score=88,
)

def test_new_reaction_replaces_the_previous_one(tmp_path, monkeypatch):
    _local_db(tmp_path, monkeypatch)
    assert database.record_outfit_feedback(**FEEDBACK_LOOK, feedback="like") == "local"
    assert database.record_outfit_feedback(**FEEDBACK_LOOK, feedback="unlike") == "local"

    feedback = database.get_style_feedback("demo-user")

    assert feedback["feedback_count"] == 1
    assert (feedback["like_count"], feedback["unlike_count"]) == (0, 1)
    assert feedback["color_scores"]["navy"] == database.UNLIKE_POINTS
    assert feedback["slot_color_scores"]["shirt"]["navy"] == database.UNLIKE_POINTS
    assert database.get_style_feedback("someone-else")["feedback_count"] == 0

def test_invalid_reaction_is_rejected(tmp_path, monkeypatch):
    _local_db(tmp_path, monkeypatch)
    import pytest

    with pytest.raises(ValueError):
        database.record_outfit_feedback(**FEEDBACK_LOOK, feedback="love")

def test_reactions_become_engine_ranking_weights(tmp_path, monkeypatch):
    _local_db(tmp_path, monkeypatch)
    assert database.feedback_user_context(database.get_style_feedback("demo-user")) is None

    database.record_outfit_feedback(**FEEDBACK_LOOK, feedback="like")
    context = database.feedback_user_context(database.get_style_feedback("demo-user"))

    assert context["preferred_color_weights"]["navy"] == 1
    assert context["slot_color_preferences"]["pants"]["beige"] == 1
    assert context["disliked_color_weights"] == {}

def test_liked_colours_rise_in_suggestions_without_changing_scores(tmp_path, monkeypatch):
    import recommendation_engine as engine

    _local_db(tmp_path, monkeypatch)
    profile = dict(skin_tone="medium", undertone="warm", style="casual", occasion="daily")
    baseline = engine.generate_outfit_suggestions(**profile, limit=5)
    liked = dict(FEEDBACK_LOOK, shirt_color="olive", pants_color="cream", shoes_color="brown")

    database.record_outfit_feedback(**liked, feedback="like")
    context = database.feedback_user_context(database.get_style_feedback("demo-user"))
    personalised = engine.generate_outfit_suggestions(**profile, limit=5, user_context=context)

    olive_rank = lambda looks: sum(look["shirt_color"] == "olive" for look in looks)
    assert olive_rank(personalised) >= olive_rank(baseline)
    for look in personalised:
        score, _ = engine.score_breakdown(**profile, shirt_color=look["shirt_color"],
                                          pants_color=look["pants_color"], shoes_color=look["shoes_color"])
        assert look["score"] == score

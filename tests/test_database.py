from __future__ import annotations

import database


class FakeSavedLookRepository:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []
        self.indexes_ensured = False

    def ensure_indexes(self) -> None:
        self.indexes_ensured = True

    def save_look(self, user_id, username, profile, outfit, source, explanation=None, metadata=None):
        payload = {
            "id": str(len(self.items) + 1),
            "user_id": user_id,
            "username": username,
            "profile": profile,
            "outfit": outfit,
            "source": source,
            "created_at": "2026-05-10T00:00:00+00:00",
            "shirt_color": outfit["shirt_color"],
            "pants_color": outfit["pants_color"],
            "shoes_color": outfit["shoes_color"],
            "score": outfit["score"],
            "skin_tone": profile["skin_tone"],
            "undertone": profile["undertone"],
            "style": profile["style"],
            "occasion": profile["occasion"],
        }
        self.items.append(payload)
        return payload

    def get_saved_looks(self, user_id):
        return [item for item in self.items if item["user_id"] == user_id]


def test_save_and_fetch_outfits(monkeypatch):
    fake_repository = FakeSavedLookRepository()
    monkeypatch.setattr(database, "_repository", lambda: fake_repository)

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
    )

    outfits = database.get_saved_outfits("demo-user")

    assert fake_repository.indexes_ensured is True
    assert len(outfits) == 1
    assert outfits[0]["shirt_color"] == "white"
    assert outfits[0]["created_at"]

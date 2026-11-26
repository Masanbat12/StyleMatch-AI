from recommendation_engine import generate_outfit_suggestions, get_recommended_colors, score_breakdown


def test_recommended_colors_are_ranked_by_weight_not_alphabetically(monkeypatch):
    import recommendation_engine as engine
    monkeypatch.setattr(engine, "_preferred_profile", lambda *args: {
        "undertone": {"best_colors": ["navy", "white"]},
        "style": {"preferred_colors": ["navy"]},
        "occasion": {"preferred_colors": ["navy"]},
    })
    monkeypatch.setattr(engine, "COLOR_THEORY_RULES", {})
    assert get_recommended_colors("cool", "elegant", "work") == ["navy", "white"]


def test_generate_outfit_suggestions_are_sorted_by_score():
    suggestions = generate_outfit_suggestions(
        skin_tone="medium",
        undertone="neutral",
        style="minimal",
        occasion="daily",
        limit=5,
    )

    scores = [outfit["score"] for outfit in suggestions]
    assert scores == sorted(scores, reverse=True)


def test_generate_outfit_suggestions_are_meaningfully_distinct():
    suggestions = generate_outfit_suggestions(
        skin_tone="medium",
        undertone="cool",
        style="elegant",
        occasion="evening",
        limit=5,
    )

    outfit_keys = {
        (outfit["shirt_color"], outfit["pants_color"], outfit["shoes_color"])
        for outfit in suggestions
    }
    assert len(outfit_keys) == len(suggestions)

    for index, outfit in enumerate(suggestions):
        for other in suggestions[index + 1 :]:
            difference_count = sum(
                outfit[key] != other[key]
                for key in ("shirt_color", "pants_color", "shoes_color")
            )
            assert difference_count >= 2


def test_score_breakdown_penalizes_avoided_colors():
    score, reasons = score_breakdown(
        skin_tone="fair",
        undertone="warm",
        style="casual",
        occasion="daily",
        shirt_color="icy blue",
        pants_color="black",
        shoes_color="white",
    )

    assert score < 70
    assert any("less flattering" in reason for reason in reasons)


def test_generate_outfit_suggestions_use_user_context_preferences():
    suggestions = generate_outfit_suggestions(
        skin_tone="medium",
        undertone="neutral",
        style="minimal",
        occasion="daily",
        limit=5,
        user_context={
            "preferred_color_weights": {"navy": 5.0},
            "disliked_color_weights": {"white": 3.0},
            "slot_color_preferences": {"shirt": {"navy": 4.0}, "pants": {}, "shoes": {}},
        },
    )

    assert suggestions[0]["shirt_color"] == "navy"


def test_nonpositive_limits_return_no_suggestions():
    for limit in (0, -1):
        assert generate_outfit_suggestions("medium", "neutral", "casual", "daily", limit=limit) == []


def test_avoided_palette_takes_priority_over_style_recommendation():
    from recommendation_engine import _palette_alignment_score
    score, reason = _palette_alignment_score("icy blue", {"icy blue"}, {"icy blue"}, {"undertone": {}})
    assert score < 0
    assert "less flattering" in reason


def test_dress_recommendations_use_single_garment_colors_and_scores():
    from recommendation_engine import generate_dress_suggestions, score_dress
    looks = generate_dress_suggestions("medium", "neutral", "casual", "daily")
    assert len(looks) == 5
    assert len({look["shirt_color"] for look in looks}) == 5
    assert [look["score"] for look in looks] == sorted([look["score"] for look in looks], reverse=True)
    for look in looks:
        assert look["shirt_color"] == look["pants_color"]
        assert look["score"] == score_dress("medium", "neutral", "casual", "daily", look["shirt_color"], look["shoes_color"])[0]
    assert generate_dress_suggestions("medium", "neutral", "casual", "daily", limit=0) == []

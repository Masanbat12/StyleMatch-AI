from recommendation_engine import generate_outfit_suggestions, get_recommended_colors, score_breakdown


def test_recommended_colors_are_ranked_by_weight_not_alphabetically():
    colors = get_recommended_colors("cool", "elegant", "work")

    assert colors[:4] == ["navy", "charcoal", "burgundy", "white"]


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

import pytest

from knowledge_base import SCORING_RULES
from recommendation_engine import (
    calculate_outfit_score,
    generate_outfit_suggestions,
    get_recommended_colors,
    score_breakdown,
    score_dress,
    score_report,
)


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
    report = score_report("fair", "warm", "elegant", "work", "icy blue", "black", "white")
    seasonal = next(item for item in report["components"] if item["id"] == "seasonal_palette")
    assert seasonal["points"] < seasonal["max"]
    assert "less flattering" in seasonal["reason"]


def test_dress_recommendations_use_single_garment_colors_and_scores():
    from recommendation_engine import generate_dress_suggestions
    looks = generate_dress_suggestions("medium", "neutral", "casual", "daily")
    assert len(looks) == 5
    assert len({look["shirt_color"] for look in looks}) == 5
    assert [look["score"] for look in looks] == sorted([look["score"] for look in looks], reverse=True)
    for look in looks:
        assert look["shirt_color"] == look["pants_color"]
        assert look["score"] == score_dress("medium", "neutral", "casual", "daily", look["shirt_color"], look["shoes_color"])[0]
    assert generate_dress_suggestions("medium", "neutral", "casual", "daily", limit=0) == []


@pytest.mark.parametrize("dress", [False, True])
def test_score_report_shape_and_totals(dress):
    profile = ("medium", "neutral", "casual", "daily")
    colors = ("soft pink", "charcoal", "navy")
    report = score_report(*profile, *colors, dress=dress)
    assert set(report) == {"score", "label", "season", "components", "strengths", "risks", "rule_ids"}
    components = report["components"]
    assert report["rule_ids"] == [item["id"] for item in components]
    assert len(set(report["rule_ids"])) == len(components)
    assert set(report["rule_ids"]) <= SCORING_RULES["rules"].keys()
    assert sum(item["max"] for item in components) == 100
    assert report["score"] == round(sum(item["points"] for item in components))
    for component in components:
        assert set(component) == {"id", "name", "points", "max", "reason"}
        assert isinstance(component["points"], float)
        assert isinstance(component["max"], float)
        assert 0 <= component["points"] <= component["max"]
        assert component["reason"]
    if dress:
        score, reasons = score_dress(*profile, colors[0], colors[2])
        assert score_report(*profile, colors[0], "red", colors[2], dress=True) == report
    else:
        score, reasons = score_breakdown(*profile, *colors)
        assert calculate_outfit_score(*profile, *colors) == score
        assert score_breakdown(*profile, *colors, user_context={"preferred_color_weights": {"navy": 9}})[0] == score
    assert score == report["score"]
    assert reasons == [item["reason"] for item in components]


def test_value_contrast_varies_by_profile():
    colors = ("black", "white", "black")
    fair = score_report("fair", "cool", "casual", "daily", *colors)
    deep = score_report("deep_dark", "warm", "casual", "daily", *colors)
    fair_value, deep_value = (
        next(item["points"] for item in report["components"] if item["id"] == "face_value")
        for report in (fair, deep)
    )
    assert fair_value < deep_value
    assert fair["score"] != deep["score"]


def test_evening_dress_code_favors_dark_anchors_over_loud_brights():
    profile = ("medium", "neutral", "elegant", "evening")
    dark = score_report(*profile, "burgundy", "navy", "black")
    bright = score_report(*profile, "red", "mustard", "cobalt")
    dark_code, bright_code = (
        next(item["points"] for item in report["components"] if item["id"] == "dress_code")
        for report in (dark, bright)
    )
    assert dark_code > bright_code
    assert dark["score"] > bright["score"]


@pytest.mark.parametrize(
    ("skin_tone", "undertone", "season"),
    [
        ("fair", "warm", "Light Spring"),
        ("light", "cool", "True Summer"),
        ("medium", "neutral", "Soft Summer"),
        ("dark", "warm", "Deep Autumn"),
        ("deep_dark", "cool", "Deep Winter"),
    ],
)
def test_score_report_maps_season(skin_tone, undertone, season):
    report = score_report(skin_tone, undertone, "casual", "daily", "white", "navy", "black")
    assert report["season"] == season


def test_baseline_scores_spread_without_losing_strong_suggestions():
    from itertools import product

    from catalog import ALL_COLORS

    profile = ("medium", "neutral", "casual", "daily")
    scores = [calculate_outfit_score(*profile, *colors) for colors in product(ALL_COLORS, repeat=3)]
    assert scores.count(100) / len(scores) <= 0.005
    assert sum(score >= 90 for score in scores) / len(scores) <= 0.10
    assert all(look["score"] >= 85 for look in generate_outfit_suggestions(*profile))

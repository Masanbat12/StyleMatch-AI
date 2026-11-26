from itertools import combinations
import json
from pathlib import Path

import pytest

from knowledge_base import COLOR_METADATA, OCCASION_RULES, SCORING_RULES
from recommendation_engine import generate_outfit_suggestions, score_report


GOLDEN_OUTFITS = json.loads(
    Path(__file__).with_name("golden_outfits.json").read_text(encoding="utf-8")
)
ANCHOR_COUNT = 12
SUGGESTION_PROFILES = tuple(tuple(case["profile"]) for case in GOLDEN_OUTFITS[:4])


RANKING_PROFILES = (
    ("medium", "neutral", "casual", "daily"),
    ("medium", "neutral", "elegant", "work"),
    ("medium", "neutral", "street", "date"),
    ("medium", "neutral", "minimal", "work"),
    ("medium", "neutral", "elegant", "evening"),
)
COLOR_SLOTS = ("shirt_color", "pants_color", "shoes_color")


def calibration_failures():
    failures = []
    for index, case in enumerate(GOLDEN_OUTFITS):
        score = score_report(*case["profile"], *case["outfit"], dress=case["dress"])["score"]
        low, high = case["band"]
        if not low <= score <= high:
            profile = "/".join(case["profile"])
            outfit = ", ".join(case["outfit"])
            failures.append((index, f"{profile} | {outfit} | got {score}, band [{low},{high}]"))
    return failures


def test_golden_calibration():
    failures = calibration_failures()
    assert len(GOLDEN_OUTFITS) >= 43
    assert not [message for index, message in failures if index < ANCHOR_COUNT]
    assert len(failures) <= len(GOLDEN_OUTFITS) * 0.1, failures


@pytest.mark.parametrize("case", GOLDEN_OUTFITS, ids=lambda case: "-".join(case["outfit"]))
def test_reasons_name_colors(case):
    report = score_report(*case["profile"], *case["outfit"], dress=case["dress"])
    for component in report["components"]:
        reason = component["reason"].lower()
        assert len(reason) <= 110
        assert "estimated range" not in reason
        assert any(color in reason for color in case["outfit"])


@pytest.mark.parametrize("profile", SUGGESTION_PROFILES)
def test_top_five_suggestions_still_score_well(profile):
    suggestions = generate_outfit_suggestions(*profile)
    assert len(suggestions) == 5
    assert all(look["score"] >= 85 for look in suggestions)



def test_top_three_change_with_style_and_occasion():
    outfits_by_profile = {
        profile: {
            tuple(look[slot] for slot in COLOR_SLOTS)
            for look in generate_outfit_suggestions(*profile, limit=3)
        }
        for profile in RANKING_PROFILES
    }
    for left, right in combinations(RANKING_PROFILES, 2):
        assert len(outfits_by_profile[left]) == len(outfits_by_profile[right]) == 3
        assert len(outfits_by_profile[left] & outfits_by_profile[right]) <= 1, (left, right)


def test_elegant_work_top_three_have_neutral_bottoms_and_no_saturated_colors():
    threshold = SCORING_RULES["rules"]["proportion"]["competition_chroma"]
    for look in generate_outfit_suggestions("medium", "neutral", "elegant", "work", limit=3):
        assert look["pants_color"] in {"navy", "charcoal", "gray", "black", "beige", "camel"}
        assert all(COLOR_METADATA[look[slot]]["chroma"] < threshold for slot in COLOR_SLOTS)


@pytest.mark.parametrize("occasion", OCCASION_RULES)
def test_street_top_three_have_one_saturated_color(occasion):
    threshold = SCORING_RULES["rules"]["proportion"]["competition_chroma"]
    looks = generate_outfit_suggestions("medium", "neutral", "street", occasion, limit=3)
    assert len(looks) == 3
    for look in looks:
        assert sum(COLOR_METADATA[look[slot]]["chroma"] >= threshold for slot in COLOR_SLOTS) == 1


def test_date_fit_rewards_the_accent_near_the_face():
    profile = ("medium", "neutral", "casual", "date")
    tops = ("soft pink", "gray")
    fits = [
        next(item["points"] for item in score_report(*profile, top, bottom, "brown")["components"]
             if item["id"] == "dress_code")
        for top, bottom in (tops, tops[::-1])
    ]
    assert fits[0] > fits[1]

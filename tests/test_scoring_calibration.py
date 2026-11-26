import json
from pathlib import Path

import pytest

from recommendation_engine import generate_outfit_suggestions, score_report


GOLDEN_OUTFITS = json.loads(
    Path(__file__).with_name("golden_outfits.json").read_text(encoding="utf-8")
)
ANCHOR_COUNT = 12
SUGGESTION_PROFILES = tuple(tuple(case["profile"]) for case in GOLDEN_OUTFITS[:4])


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
    assert len(GOLDEN_OUTFITS) >= 34
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


"""Print the golden-set results, baseline score spread and generated scores."""

from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from catalog import ALL_COLORS
from recommendation_engine import generate_outfit_suggestions, score_breakdown
from test_scoring_calibration import (
    COLOR_SLOTS,
    GOLDEN_OUTFITS,
    RANKING_PROFILES,
    SUGGESTION_PROFILES,
    calibration_failures,
)


def main():
    failures = calibration_failures()
    print(f"Golden set: passed {len(GOLDEN_OUTFITS) - len(failures)}/{len(GOLDEN_OUTFITS)}")
    for _, message in failures:
        print(message)

    profile = ("medium", "neutral", "casual", "daily")
    scores = [score_breakdown(*profile, *colors)[0] for colors in product(ALL_COLORS, repeat=3)]
    at_100 = scores.count(100) / len(scores)
    at_least_90 = sum(score >= 90 for score in scores) / len(scores)
    print(f"Distribution: {min(scores)}-{max(scores)}, 100: {at_100:.2%}, >=90: {at_least_90:.2%}")
    for suggestion_profile in SUGGESTION_PROFILES:
        top_five = [look["score"] for look in generate_outfit_suggestions(*suggestion_profile)]
        print(f"{'/'.join(suggestion_profile)}: {top_five}")

    for ranking_profile in RANKING_PROFILES:
        looks = generate_outfit_suggestions(*ranking_profile, limit=3)
        summaries = ["/".join(look[slot] for slot in COLOR_SLOTS) + f" ({look['score']})" for look in looks]
        print(f"Top 3 {'/'.join(ranking_profile)}: {', '.join(summaries)}")


if __name__ == "__main__":
    main()


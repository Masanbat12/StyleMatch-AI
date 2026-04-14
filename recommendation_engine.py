from __future__ import annotations

from typing import Dict, List, Tuple
from itertools import product

from knowledge_base import GROUNDED_RULES, STYLE_RULES, OCCASION_RULES

ALL_COLORS = [
    "white", "black", "gray", "blue", "navy", "olive", "beige", "cream",
    "brown", "rust", "mustard", "forest green", "burgundy", "icy blue",
    "taupe", "green", "soft pink", "red", "cobalt", "charcoal", "camel",
    "deep green",
]

COLOR_BRIGHTNESS: Dict[str, int] = {
    "white": 96,
    "cream": 92,
    "icy blue": 88,
    "beige": 82,
    "soft pink": 80,
    "taupe": 70,
    "camel": 66,
    "gray": 62,
    "mustard": 60,
    "blue": 58,
    "olive": 50,
    "green": 48,
    "red": 45,
    "cobalt": 42,
    "rust": 40,
    "brown": 28,
    "navy": 24,
    "charcoal": 20,
    "forest green": 20,
    "burgundy": 18,
    "deep green": 16,
    "black": 8,
}

SKIN_BRIGHTNESS = {
    "very_fair": 94,
    "fair": 88,
    "light": 79,
    "light_medium": 70,
    "medium": 58,
    "tan": 46,
    "deep_tan": 36,
    "dark": 24,
    "deep_dark": 14,
}

SKIN_TONE_OPTIONS = list(SKIN_BRIGHTNESS.keys())
NEUTRAL_SHOE_COLORS = {"white", "black", "brown", "beige"}


def get_recommended_colors(undertone: str, style: str, occasion: str) -> List[str]:
    colors = set(GROUNDED_RULES.get(undertone, {}).get("best", ["black", "white"]))
    colors.update(STYLE_RULES.get(style, []))
    colors.update(OCCASION_RULES.get(occasion, []))
    return sorted(colors)


def get_avoid_colors(undertone: str) -> List[str]:
    return GROUNDED_RULES.get(undertone, {}).get("avoid", [])


def describe_contrast(skin_tone: str, color_name: str) -> tuple[int, str]:
    skin_value = SKIN_BRIGHTNESS.get(skin_tone, 58)
    cloth_value = COLOR_BRIGHTNESS.get(color_name, 50)
    contrast_gap = abs(skin_value - cloth_value)

    if contrast_gap >= 45:
        return 8, "high contrast"
    if contrast_gap >= 20:
        return 5, "balanced contrast"
    return 1, "low contrast"


def score_breakdown(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
) -> Tuple[int, List[str]]:
    recommended = set(get_recommended_colors(undertone, style, occasion))
    avoided = set(get_avoid_colors(undertone))
    score = 45
    reasons: List[str] = []

    for label, color in {
        "Shirt": shirt_color,
        "Pants": pants_color,
        "Shoes": shoes_color,
    }.items():
        if color in recommended:
            score += 11
            reasons.append(f"{label} color '{color}' matches your undertone/style profile.")
        elif color in avoided:
            score -= 9
            reasons.append(f"{label} color '{color}' is less flattering for this undertone.")

    shirt_bonus, shirt_contrast = describe_contrast(skin_tone, shirt_color)
    score += shirt_bonus
    reasons.append(f"Shirt-to-skin contrast is {shirt_contrast}.")

    pants_bonus, pants_contrast = describe_contrast(skin_tone, pants_color)
    score += max(0, pants_bonus - 2)
    reasons.append(f"Pants-to-skin contrast is {pants_contrast}.")

    if shoes_color in NEUTRAL_SHOE_COLORS:
        score += 6
        reasons.append("Neutral shoes improve versatility.")

    if shirt_color != pants_color:
        score += 7
        reasons.append("Top and bottom separation improves depth.")
    else:
        score -= 4
        reasons.append("Matching top and bottom exactly can flatten the look.")

    if len({shirt_color, pants_color, shoes_color}) == 1:
        score -= 8
        reasons.append("Using one color for every item reduces visual interest.")

    score = max(0, min(score, 100))
    return score, reasons


def calculate_outfit_score(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
) -> int:
    score, _ = score_breakdown(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
    )
    return score


def generate_outfit_suggestions(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    limit: int = 5,
) -> List[dict]:
    recommended = get_recommended_colors(undertone, style, occasion)
    top_candidates = recommended[:8] if len(recommended) >= 8 else recommended
    pant_candidates = [c for c in ["black", "navy", "gray", "beige", "charcoal", "brown"] if c in ALL_COLORS]
    shoe_candidates = [c for c in ["white", "black", "brown", "beige"] if c in ALL_COLORS]

    candidates = []
    seen = set()

    for shirt_color, pants_color, shoes_color in product(top_candidates, pant_candidates, shoe_candidates):
        outfit_key = (shirt_color, pants_color, shoes_color)
        if outfit_key in seen:
            continue
        seen.add(outfit_key)

        score = calculate_outfit_score(
            skin_tone=skin_tone,
            undertone=undertone,
            style=style,
            occasion=occasion,
            shirt_color=shirt_color,
            pants_color=pants_color,
            shoes_color=shoes_color,
        )

        candidates.append({
            "shirt_color": shirt_color,
            "pants_color": pants_color,
            "shoes_color": shoes_color,
            "score": score,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]

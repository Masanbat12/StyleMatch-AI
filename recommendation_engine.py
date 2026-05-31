from __future__ import annotations

from itertools import product
from typing import Any

from catalog import ALL_COLORS, NEUTRAL_SHOE_COLORS, SKIN_BRIGHTNESS, SKIN_TONE_OPTIONS
from knowledge_base import (
    COLOR_METADATA,
    COLOR_THEORY_RULES,
    EXPLANATION_TEMPLATES,
    OCCASION_RULES,
    STYLE_RULES,
    UNDERTONE_RULES,
)


def _humanize(value: str) -> str:
    return value.replace("_", " ").title()


def _color_brightness(color_name: str) -> int:
    return int(COLOR_METADATA.get(color_name, {}).get("brightness", 50))


def _color_family(color_name: str) -> str:
    return str(COLOR_METADATA.get(color_name, {}).get("family", color_name))


def _color_temperature(color_name: str) -> str:
    return str(COLOR_METADATA.get(color_name, {}).get("temperature", "neutral"))


def _preferred_profile(undertone: str, style: str, occasion: str) -> dict[str, Any]:
    return {
        "undertone": UNDERTONE_RULES.get(undertone, {}),
        "style": STYLE_RULES.get(style, {}),
        "occasion": OCCASION_RULES.get(occasion, {}),
    }


def _bounded(value: float, lower: int, upper: int) -> int:
    return max(lower, min(upper, round(value)))


def _feedback_color_points(
    feedback_context: dict[str, Any] | None,
    color: str,
    slot: str | None = None,
) -> float:
    if not feedback_context:
        return 0.0

    color_scores = feedback_context.get("color_scores", {})
    points = float(color_scores.get(color, 0))
    if slot:
        slot_scores = feedback_context.get("slot_color_scores", {}).get(slot, {})
        points += float(slot_scores.get(color, 0)) * 1.15
    return points


def _feedback_rank_adjustment(feedback_context: dict[str, Any] | None, color: str) -> int:
    points = _feedback_color_points(feedback_context, color, slot="shirt")
    return _bounded(points * 0.9, -14, 16)


def _feedback_alignment_score(
    feedback_context: dict[str, Any] | None,
    slot: str,
    color: str,
) -> tuple[int, str | None]:
    points = _feedback_color_points(feedback_context, color, slot=slot)
    if points >= 8:
        return 10, f"{_humanize(color)} is boosted by your previous likes."
    if points >= 4:
        return 5, f"{_humanize(color)} reflects a color you have liked before."
    if points <= -8:
        return -15, f"{_humanize(color)} is reduced because you marked similar looks as not for you."
    if points <= -4:
        return -8, f"{_humanize(color)} is slightly reduced by your feedback history."
    return 0, None


def _outfit_feedback_strength(
    feedback_context: dict[str, Any] | None,
    outfit: dict[str, Any],
) -> float:
    return (
        _feedback_color_points(feedback_context, outfit["shirt_color"], "shirt")
        + _feedback_color_points(feedback_context, outfit["pants_color"], "pants")
        + _feedback_color_points(feedback_context, outfit["shoes_color"], "shoes")
    )


def get_recommended_colors(
    undertone: str,
    style: str,
    occasion: str,
    feedback_context: dict[str, Any] | None = None,
) -> list[str]:
    profile = _preferred_profile(undertone, style, occasion)
    weighted_colors: dict[str, int] = {}

    for color in profile["undertone"].get("best_colors", []):
        weighted_colors[color] = weighted_colors.get(color, 0) + 5
    for color in profile["undertone"].get("secondary_colors", []):
        weighted_colors[color] = weighted_colors.get(color, 0) + 2
    for color in profile["undertone"].get("recommended_neutrals", []):
        weighted_colors[color] = weighted_colors.get(color, 0) + 2
    for color in profile["style"].get("preferred_colors", []):
        weighted_colors[color] = weighted_colors.get(color, 0) + 3
    for color in profile["occasion"].get("preferred_colors", []):
        weighted_colors[color] = weighted_colors.get(color, 0) + 3
    for left, right in COLOR_THEORY_RULES.get("universal_pairs", []):
        weighted_colors[left] = weighted_colors.get(left, 0) + 1
        weighted_colors[right] = weighted_colors.get(right, 0) + 1
    if feedback_context:
        for color in ALL_COLORS:
            adjustment = _feedback_rank_adjustment(feedback_context, color)
            if adjustment:
                weighted_colors[color] = weighted_colors.get(color, 0) + adjustment
    ranked_colors = sorted(
        weighted_colors.items(),
        key=lambda item: (-item[1], -_color_brightness(item[0]), item[0]),
    )
    return [color for color, _ in ranked_colors]


def get_avoid_colors(undertone: str) -> list[str]:
    return UNDERTONE_RULES.get(undertone, {}).get("avoid_colors", [])


def describe_contrast(skin_tone: str, color_name: str) -> tuple[int, str]:
    skin_value = SKIN_BRIGHTNESS.get(skin_tone, 58)
    cloth_value = _color_brightness(color_name)
    contrast_gap = abs(skin_value - cloth_value)

    if contrast_gap >= 45:
        return 8, "high contrast"
    if contrast_gap >= 20:
        return 5, "balanced contrast"
    return 1, "low contrast"


def _palette_alignment_score(color: str, recommended: set[str], avoided: set[str], profile: dict[str, Any]) -> tuple[int, str | None]:
    if color in avoided:
        return -24, f"{color} is less flattering for your undertone palette."
    if color in recommended:
        return 11, f"{color} supports your undertone and styling direction."
    if color in profile["undertone"].get("recommended_neutrals", []):
        return 5, f"{color} acts as a stable neutral for your profile."
    return 0, None


def _evaluate_harmony(shirt_color: str, pants_color: str) -> tuple[int, str | None, str | None]:
    harmonies = COLOR_THEORY_RULES.get("harmonies", {})
    universal_pairs = {tuple(pair) for pair in COLOR_THEORY_RULES.get("universal_pairs", [])}

    if (shirt_color, pants_color) in universal_pairs or (pants_color, shirt_color) in universal_pairs:
        return 10, "universal", f"{shirt_color} and {pants_color} form a proven, easy-to-wear pairing."

    shirt_family = _color_family(shirt_color)
    pants_family = _color_family(pants_color)

    analogous_targets = set(harmonies.get("analogous", {}).get(shirt_color, []))
    analogous_targets.update(harmonies.get("analogous", {}).get(shirt_family, []))
    if pants_color in analogous_targets or pants_family in analogous_targets:
        return 8, "analogous", f"{shirt_color} and {pants_color} stay close on the palette, which keeps the look cohesive."

    complementary_targets = set(harmonies.get("complementary", {}).get(shirt_color, []))
    complementary_targets.update(harmonies.get("complementary", {}).get(shirt_family, []))
    if pants_color in complementary_targets or pants_family in complementary_targets:
        return 9, "complementary", f"{shirt_color} and {pants_color} create a controlled complementary contrast."

    monochromatic_targets = set(harmonies.get("monochromatic", {}).get(shirt_color, []))
    monochromatic_targets.update(harmonies.get("monochromatic", {}).get(shirt_family, []))
    if pants_color in monochromatic_targets or pants_family in monochromatic_targets or shirt_family == pants_family:
        return 6, "monochromatic", f"{shirt_color} and {pants_color} keep the palette focused in one tonal family."

    if shirt_color != pants_color:
        return 3, None, "The top and bottom stay visually separated, which helps the silhouette read clearly."

    return -4, None, "Matching the top and bottom exactly can flatten the look."


def _shoe_score(shoes_color: str, profile: dict[str, Any]) -> tuple[int, str]:
    style_preferences = set(profile["style"].get("preferred_shoes", []))
    occasion_preferences = set(profile["occasion"].get("preferred_shoes", []))
    score = 0

    if shoes_color in style_preferences:
        score += 5
    if shoes_color in occasion_preferences:
        score += 5
    if shoes_color in NEUTRAL_SHOE_COLORS:
        score += 4
        return score, f"{shoes_color} shoes keep the outfit versatile and easy to wear."
    return score, f"{shoes_color} shoes add a stronger accent while still finishing the outfit."


def _contrast_reason(skin_tone: str, shirt_color: str) -> str:
    _, shirt_contrast = describe_contrast(skin_tone, shirt_color)
    if shirt_contrast == "high contrast":
        return f"{_humanize(shirt_color)} creates clean contrast against {_humanize(skin_tone)} skin."
    if shirt_contrast == "balanced contrast":
        return f"{_humanize(shirt_color)} keeps the contrast balanced against {_humanize(skin_tone)} skin."
    return f"{_humanize(shirt_color)} keeps the top layer soft and close in visual intensity."


def build_outfit_explanation(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    harmony_label: str | None = None,
) -> str:
    shirt_template = EXPLANATION_TEMPLATES["shirt_reasons"][0]
    pants_template = EXPLANATION_TEMPLATES["pants_reasons"][0]
    shoes_template = EXPLANATION_TEMPLATES["shoes_reasons"][0]
    outfit_template = EXPLANATION_TEMPLATES["full_outfit_reasons"][0]

    shirt_sentence = shirt_template.format(
        shirt=_humanize(shirt_color),
        undertone=_humanize(undertone).lower(),
        style=_humanize(style).lower(),
    )
    pants_sentence = pants_template.format(pants=_humanize(pants_color))
    shoes_sentence = shoes_template.format(shoes=_humanize(shoes_color))
    outfit_sentence = outfit_template.format(
        shirt=_humanize(shirt_color).lower(),
        pants=_humanize(pants_color).lower(),
        occasion=_humanize(occasion).lower(),
        style=_humanize(style).lower(),
        undertone=_humanize(undertone).lower(),
    )

    contrast_sentence = _contrast_reason(skin_tone, shirt_color)
    if harmony_label == "analogous":
        harmony_sentence = f"{_humanize(shirt_color)} and {_humanize(pants_color).lower()} stay in a close tonal range, which keeps the palette calm."
    elif harmony_label == "complementary":
        harmony_sentence = f"{_humanize(shirt_color)} and {_humanize(pants_color).lower()} create a more intentional color contrast without feeling harsh."
    elif harmony_label == "monochromatic":
        harmony_sentence = f"{_humanize(shirt_color)} and {_humanize(pants_color).lower()} keep the outfit within a tight tonal family."
    else:
        harmony_sentence = outfit_sentence

    return " ".join([contrast_sentence, harmony_sentence, shoes_sentence])


def _outfit_difference(candidate: dict[str, Any], existing: dict[str, Any]) -> int:
    return sum(
        candidate[key] != existing[key]
        for key in ("shirt_color", "pants_color", "shoes_color")
    )


def _is_meaningfully_distinct(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> bool:
    for existing in selected:
        if _outfit_difference(candidate, existing) < 2:
            return False
        if (
            candidate["shirt_color"] == existing["shirt_color"]
            and candidate["harmony"] == existing["harmony"]
        ):
            return False
    return True


def score_breakdown(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    feedback_context: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    profile = _preferred_profile(undertone, style, occasion)
    recommended = set(get_recommended_colors(undertone, style, occasion, feedback_context=feedback_context))
    avoided = set(get_avoid_colors(undertone))
    score = 45
    reasons: list[str] = []

    for label, color in {"Shirt": shirt_color, "Pants": pants_color, "Shoes": shoes_color}.items():
        color_score, color_reason = _palette_alignment_score(color, recommended, avoided, profile)
        score += color_score
        if color_reason:
            reasons.append(f"{label}: {color_reason}")
        feedback_score, feedback_reason = _feedback_alignment_score(feedback_context, label.lower(), color)
        score += feedback_score
        if feedback_reason:
            reasons.append(f"{label}: {feedback_reason}")

    harmony_score, _, harmony_reason = _evaluate_harmony(shirt_color, pants_color)
    score += harmony_score
    if harmony_reason:
        reasons.append(harmony_reason)

    shirt_bonus, shirt_contrast = describe_contrast(skin_tone, shirt_color)
    score += shirt_bonus
    reasons.append(f"Shirt contrast is {shirt_contrast}, which influences how defined the top looks.")

    pants_bonus, pants_contrast = describe_contrast(skin_tone, pants_color)
    score += max(0, pants_bonus - 2)
    reasons.append(f"Pants contrast is {pants_contrast}, which affects how grounded the base feels.")

    shoes_bonus, shoes_reason = _shoe_score(shoes_color, profile)
    score += shoes_bonus
    reasons.append(shoes_reason)

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
    feedback_context: dict[str, Any] | None = None,
) -> int:
    score, _ = score_breakdown(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
        feedback_context=feedback_context,
    )
    return score


def generate_outfit_suggestions(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    limit: int = 5,
    feedback_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    profile = _preferred_profile(undertone, style, occasion)
    recommended = get_recommended_colors(undertone, style, occasion, feedback_context=feedback_context)
    top_candidates = recommended[:10] if len(recommended) >= 10 else recommended
    pant_candidates = [
        color
        for color in dict.fromkeys(
            profile["undertone"].get("recommended_neutrals", [])
            + profile["style"].get("preferred_colors", [])
            + profile["occasion"].get("preferred_colors", [])
            + ["black", "navy", "gray", "beige", "charcoal", "brown", "taupe"]
        )
        if color in ALL_COLORS
    ]
    shoe_candidates = [
        color
        for color in dict.fromkeys(
            profile["style"].get("preferred_shoes", [])
            + profile["occasion"].get("preferred_shoes", [])
            + ["white", "black", "brown", "beige", "gray"]
        )
        if color in ALL_COLORS
    ]

    candidates: list[dict[str, Any]] = []
    seen = set()

    for shirt_color, pants_color, shoes_color in product(top_candidates, pant_candidates, shoe_candidates):
        outfit_key = (shirt_color, pants_color, shoes_color)
        if outfit_key in seen:
            continue
        seen.add(outfit_key)

        score, reasons = score_breakdown(
            skin_tone=skin_tone,
            undertone=undertone,
            style=style,
            occasion=occasion,
            shirt_color=shirt_color,
            pants_color=pants_color,
            shoes_color=shoes_color,
            feedback_context=feedback_context,
        )
        _, harmony_label, _ = _evaluate_harmony(shirt_color, pants_color)
        explanation = build_outfit_explanation(
            skin_tone=skin_tone,
            undertone=undertone,
            style=style,
            occasion=occasion,
            shirt_color=shirt_color,
            pants_color=pants_color,
            shoes_color=shoes_color,
            harmony_label=harmony_label,
        )

        candidates.append(
            {
                "shirt_color": shirt_color,
                "pants_color": pants_color,
                "shoes_color": shoes_color,
                "score": score,
                "explanation": explanation,
                "reasons": reasons,
                "harmony": harmony_label or "balanced",
            }
        )

    candidates.sort(
        key=lambda outfit: (
            -outfit["score"],
            -_outfit_feedback_strength(feedback_context, outfit),
            recommended.index(outfit["shirt_color"]) if outfit["shirt_color"] in recommended else 999,
            outfit["pants_color"],
            outfit["shoes_color"],
        )
    )

    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        if _is_meaningfully_distinct(candidate, selected):
            selected.append(candidate)
        if len(selected) == limit:
            break

    if len(selected) < limit:
        seen_keys = {
            (outfit["shirt_color"], outfit["pants_color"], outfit["shoes_color"])
            for outfit in selected
        }
        for candidate in candidates:
            candidate_key = (
                candidate["shirt_color"],
                candidate["pants_color"],
                candidate["shoes_color"],
            )
            if candidate_key in seen_keys:
                continue
            selected.append(candidate)
            seen_keys.add(candidate_key)
            if len(selected) == limit:
                break

    return selected

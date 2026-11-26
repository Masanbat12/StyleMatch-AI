from __future__ import annotations

from itertools import product
from typing import Any

from catalog import ALL_COLORS, SKIN_BRIGHTNESS
from knowledge_base import (
    COLOR_METADATA,
    COLOR_THEORY_RULES,
    SCORING_RULES,
    SEASONAL_PALETTES,
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


def _slot_preference_weight(user_context: dict[str, Any] | None, slot: str, color: str) -> float:
    if not user_context:
        return 0.0
    slot_preferences = user_context.get("slot_color_preferences", {})
    return float(slot_preferences.get(slot, {}).get(color, 0.0))


def _personalization_bonus(
    user_context: dict[str, Any] | None,
    slot: str,
    color: str,
) -> int:
    if not user_context:
        return 0

    preferred = float(user_context.get("preferred_color_weights", {}).get(color, 0.0))
    disliked = float(user_context.get("disliked_color_weights", {}).get(color, 0.0))
    slot_weight = _slot_preference_weight(user_context, slot, color)
    net = preferred + (slot_weight * 1.15) - (disliked * 1.1)

    if net >= 4.0:
        return 8
    if net >= 2.0:
        return 4
    if net <= -2.8:
        return -7
    return 0


def get_recommended_colors(
    undertone: str,
    style: str,
    occasion: str,
    user_context: dict[str, Any] | None = None,
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
    if user_context:
        for color, weight in user_context.get("preferred_color_weights", {}).items():
            weighted_colors[color] = weighted_colors.get(color, 0) + round(float(weight) * 1.3)
        for color, weight in user_context.get("disliked_color_weights", {}).items():
            weighted_colors[color] = weighted_colors.get(color, 0) - round(float(weight) * 1.2)

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


def _season_profile(skin_tone: str, undertone: str) -> tuple[int, str, dict[str, Any]]:
    value = SKIN_BRIGHTNESS.get(skin_tone, SEASONAL_PALETTES["skin_value_default"])
    row = next(row for row in SEASONAL_PALETTES["mapping"] if value >= row["min_value"])
    season = row.get(undertone, row["neutral"])
    return value, season, SEASONAL_PALETTES["palettes"][season]


def _color_chroma(color: str) -> int:
    return COLOR_METADATA.get(color, {}).get("chroma", 0)


def _range_fit(value: int, bounds: list[int], tolerance: int) -> tuple[float, str]:
    low, high = bounds
    if value < low:
        return max(0, 1 - (low - value) / tolerance), "below"
    if value > high:
        return max(0, 1 - (value - high) / tolerance), "above"
    return 1, "within"


def _harmony(top: str, bottom: str) -> str:
    families = _color_family(top), _color_family(bottom)
    if families[0] == families[1]:
        return "monochromatic"
    if "neutral" in families:
        return "neutral-anchored"
    rule = SCORING_RULES["rules"]["harmony"]
    hues = rule["hues"]
    if all(family in hues for family in families):
        gap = abs(hues[families[0]] - hues[families[1]])
        gap = min(gap, 360 - gap)
        if gap <= rule["analogous_angle"]:
            return "analogous"
        if 180 - gap <= rule["complementary_angle"]:
            return "complementary"
    return "mixed"


def score_report(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    dress: bool = False,
) -> dict[str, Any]:
    """Score colors using the dress as the main garment and base in dress mode."""
    rules = SCORING_RULES["rules"]
    skin_value, season, palette = _season_profile(skin_tone, undertone)
    top = shirt_color
    base = top if dress else pants_color
    shoes = shoes_color
    garment = "Dress" if dress else "Top"
    top_value, base_value = _color_brightness(top), _color_brightness(base)
    top_chroma, base_chroma, shoes_chroma = map(_color_chroma, (top, base, shoes))
    components = []

    def add(rule_id: str, fit: float, reason: str) -> None:
        rule = rules[rule_id]
        maximum = float(rule.get("dress_max", rule["max"]) if dress else rule["max"])
        components.append(dict(id=rule_id, name=rule["name"], points=round(fit * maximum, 2),
                               max=maximum, reason=reason))

    fit, position = _range_fit(abs(skin_value - top_value), palette["face_value"],
                               rules["face_value"]["tolerance"])
    add("face_value", fit, f"{garment}-to-skin contrast is {position} the estimated range.")
    if not dress:
        fit, position = _range_fit(abs(top_value - base_value), palette["outfit_value"],
                                   rules["outfit_value"]["tolerance"])
        add("outfit_value", fit, f"Top-to-bottom contrast is {position} the estimated range.")

    chroma = rules["chroma"]
    fit, position = _range_fit(top_chroma, palette["chroma"], chroma["tolerance"])
    reason = f"{garment} saturation is {position} the estimated range."
    if not dress:
        base_fit, base_position = _range_fit(base_chroma, palette["chroma"], chroma["tolerance"])
        weight = chroma["secondary_weight"]
        if (1 - base_fit) * weight > (1 - fit) * (1 - weight):
            reason = f"Bottom saturation is {base_position} the estimated range."
        fit = fit * (1 - weight) + base_fit * weight
    add("chroma", fit, reason)

    temperature = rules["temperature"]
    temperature_fit = temperature["fit"].get(undertone, temperature["fit"]["neutral"])
    top_temperature, base_temperature = map(_color_temperature, (top, base))
    weight = temperature["secondary_weight"] if not dress else 0
    fit = temperature_fit[top_temperature] * (1 - weight) + temperature_fit[base_temperature] * weight
    reason = f"{garment} has a {top_temperature} color temperature."
    if temperature_fit[base_temperature] < temperature_fit[top_temperature] and weight:
        reason = f"The {base_temperature} bottom shifts the outfit temperature away from your palette."
    add("temperature", fit, reason)

    seasonal = rules["seasonal_palette"]
    avoid = palette["avoid"] + get_avoid_colors(undertone)
    top_status = _palette_status(top, palette["best"], avoid)
    base_status = _palette_status(base, palette["best"], avoid)
    weight = seasonal["secondary_weight"] if not dress else 0
    values = seasonal["fit"]
    fit = values[top_status] * (1 - weight) + values[base_status] * weight
    palette_name = season.title()
    if top_status == "avoid":
        reason = f"{_humanize(top)} is less flattering for this palette."
    elif base_status == "avoid":
        reason = f"{_humanize(base)} is less flattering for this palette."
    elif top_status == "best":
        reason = f"{_humanize(top)} is a recommended {palette_name} color."
    else:
        reason = f"{_humanize(top)} sits outside the core {palette_name} colors."
    add("seasonal_palette", fit, reason)

    harmony = _harmony(top, shoes if dress else base)
    harmony_reasons = {
        "monochromatic": "The pair shares a color family.",
        "analogous": "The hues sit near each other on the color wheel.",
        "complementary": "The hues sit across the color wheel.",
        "neutral-anchored": "A neutral color anchors the pairing.",
        "mixed": "The hues form a mixed pairing.",
    }
    add("harmony", rules["harmony"]["fit"][harmony], harmony_reasons[harmony])

    proportion = rules["proportion"]
    shares = proportion["dress_shares"] if dress else proportion["shares"]
    footwear = rules["footwear"]
    statement = style in footwear["statement_styles"]
    loud = shoes_chroma >= max(top_chroma, base_chroma) + proportion["chroma_lead"]
    proportion_result, reason = "balanced", "The main garment leads the palette."
    if loud and not statement and shares["shoes"] <= proportion["max_accent_share"]:
        proportion_result, reason = "dominant_shoes", "The shoes dominate the color emphasis."
    elif (
        not dress
        and harmony in {"complementary", "mixed"}
        and min(top_chroma, base_chroma) >= proportion["competition_chroma"]
        and min(shares["top"], shares["bottom"]) > proportion["max_accent_share"]
    ):
        proportion_result, reason = "competing_garments", "Two large areas of vivid color compete."
    elif loud:
        reason = "The shoes provide a small statement accent."
    add("proportion", proportion["fit"][proportion_result], reason)

    dress_code = rules["dress_code"]
    code = dress_code["codes"].get(occasion, dress_code["codes"]["daily"])
    anchor = base in footwear["anchor_colors"] or base in footwear["dark_anchors"]
    if base_value > code["base_value"]:
        level, reason = "poor", f"The base color is too light for {occasion}."
    elif code["anchor_required"] and not anchor:
        level, reason = "poor", f"The base lacks an anchor color for {occasion}."
    elif shoes_chroma > code["shoe_chroma"]:
        level, reason = "acceptable", f"The shoe color is bold for {occasion}."
    elif max(top_chroma, base_chroma) > code["garment_chroma"]:
        level, reason = "acceptable", f"A garment color is vivid for {occasion}."
    else:
        level, reason = "preferred", f"The palette fits the {occasion} color guidelines."
    add("dress_code", dress_code["fit"][level], reason)

    if loud and not statement:
        level, reason = "loud", "The shoes are the most saturated item."
    elif shoes == base or shoes in footwear["anchor_colors"]:
        level, reason = "anchored", "The shoes anchor the base color."
    elif loud:
        level, reason = "statement", "The shoes add a streetwear accent."
    else:
        level, reason = "unanchored", "The shoes introduce a separate accent color."
    add("footwear", footwear["fit"][level], reason)

    score = round(sum(component["points"] for component in components))
    label = next(label for floor, label in SCORING_RULES["labels"].items() if score >= int(floor))
    return {
        "score": score,
        "label": label,
        "season": season.title(),
        "components": components,
        "strengths": [item["reason"] for item in components if item["points"] == item["max"]],
        "risks": [item["reason"] for item in components if item["points"] < item["max"]],
        "rule_ids": [item["id"] for item in components],
    }


def _palette_status(color: str, best: list[str], avoid: list[str]) -> str:
    if color in avoid:
        return "avoid"
    return "best" if color in best else "other"


def _report_breakdown(report: dict[str, Any]) -> tuple[int, list[str]]:
    return report["score"], [item["reason"] for item in report["components"]]


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
    user_context: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    """Return the grounded score. Saved preferences affect suggestion ranking."""
    return _report_breakdown(
        score_report(skin_tone, undertone, style, occasion, shirt_color, pants_color, shoes_color)
    )


def calculate_outfit_score(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    user_context: dict[str, Any] | None = None,
) -> int:
    score, _ = score_breakdown(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
        user_context=user_context,
    )
    return score


def generate_outfit_suggestions(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    limit: int = 5,
    user_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    profile = _preferred_profile(undertone, style, occasion)
    recommended = get_recommended_colors(undertone, style, occasion, user_context=user_context)
    _, _, palette = _season_profile(skin_tone, undertone)
    top_candidates = [color for color in dict.fromkeys(recommended[:10] + palette["best"])
                      if color in ALL_COLORS]
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
    for shirt_color, pants_color, shoes_color in product(top_candidates, pant_candidates, shoe_candidates):
        score, reasons = score_breakdown(
            skin_tone=skin_tone,
            undertone=undertone,
            style=style,
            occasion=occasion,
            shirt_color=shirt_color,
            pants_color=pants_color,
            shoes_color=shoes_color,
            user_context=user_context,
        )
        harmony_label = _harmony(shirt_color, pants_color)
        explanation = " ".join(reasons)

        candidates.append(
            {
                "shirt_color": shirt_color,
                "pants_color": pants_color,
                "shoes_color": shoes_color,
                "score": score,
                "explanation": explanation,
                "reasons": reasons,
                "harmony": harmony_label or "balanced",
                "personalized": user_context is not None,
            }
        )

    candidates.sort(
        key=lambda outfit: (
            -outfit["score"] - sum(
                weight * _personalization_bonus(user_context, slot, outfit[f"{slot}_color"])
                for slot, weight in SCORING_RULES["preference_rank_weights"].items()
            ),
            -outfit["score"],
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


def score_dress(skin_tone, undertone, style, occasion, dress_color, shoes_color):
    return _report_breakdown(
        score_report(skin_tone, undertone, style, occasion, dress_color, dress_color, shoes_color, dress=True)
    )


def generate_dress_suggestions(skin_tone, undertone, style, occasion, limit=5):
    if limit <= 0:
        return []
    outfits = []
    _, _, palette = _season_profile(skin_tone, undertone)
    colors = dict.fromkeys(get_recommended_colors(undertone, style, occasion) + palette["best"])
    for color in colors:
        best = None
        for shoe in ("white", "black", "brown", "beige", "gray"):
            score, reasons = score_dress(skin_tone, undertone, style, occasion, color, shoe)
            candidate = dict(shirt_color=color, pants_color=color, shoes_color=shoe, score=score,
                             reasons=reasons, harmony="dress palette",
                             explanation=f"{_humanize(color)} dress with {_humanize(shoe).lower()} shoes. " + " ".join(reasons))
            if best is None or score > best["score"]:
                best = candidate
        outfits.append(best)
    return sorted(outfits, key=lambda outfit: -outfit["score"])[:limit]

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


def _profile_color_fit(
    profile: dict[str, Any],
    rule: dict[str, Any],
    top: str,
    base: str,
    shoes: str,
    dress: bool,
    skin_value: int,
    top_status: str,
) -> tuple[float, str]:
    config = profile["scoring"]
    neutrals = SCORING_RULES["rules"]["footwear"]["anchor_colors"]
    threshold = SCORING_RULES["rules"]["proportion"]["competition_chroma"]
    garments = (top,) if dress else (top, base)
    colors = (*garments, shoes)
    vivid = [color for color in colors if _color_chroma(color) >= threshold]
    bases = config.get("bases", [])
    accents = [color for color in garments if color not in bases]
    top_value, base_value = map(_color_brightness, (top, base))
    top_name = _humanize(top)
    base_item = f"{_humanize(base)} {'dress' if dress else 'bottom'}"
    shoe_item = f"{_humanize(shoes)} shoes"
    pair = f"{top_name} and {_humanize(shoes if dress else base).lower()}"
    contrast = abs(top_value - _color_brightness(shoes if dress else base))
    tolerance = rule["value_tolerance"]

    def band_fit(key: str, value: int) -> float:
        return _range_fit(value, config.get(key, [0, 100]), tolerance)[0]

    checks = {
        "base": (base in bases, f"{base_item} color for the profile"),
        "base_value": (band_fit("base_value", base_value), f"{base_item} lightness"),
        "top_value": (band_fit("top_value", top_value), f"{top_name} garment lightness"),
        "contrast": (band_fit("contrast", contrast), f"{pair} contrast"),
        "face_contrast": (band_fit("face_contrast", abs(skin_value - top_value)), f"{top_name} contrast against the face"),
        "muted_garments": (
            max(map(_color_chroma, garments)) <= config.get("max_garment_chroma", 100),
            f"{pair} garment intensity",
        ),
        "max_vivid": (len(vivid) <= config.get("max_vivid", len(colors)), f"{pair} palette intensity"),
        "shoes": (shoes in profile["preferred_shoes"], f"{shoe_item} for the profile"),
        "single_vivid": (len(vivid) == 1, f"{pair} palette with one saturated accent"),
        "street_base": (
            all(color in bases for color in garments if color not in vivid),
            f"{pair} streetwear base",
        ),
        "neutral_palette": (all(color in neutrals for color in colors), f"{pair} neutral palette"),
        "soft_accent": (
            len(accents) <= 1 and all(_color_chroma(color) <= config.get("max_garment_chroma", 100)
                                      for color in accents),
            f"{pair} palette with at most one soft accent",
        ),
        "face_accent": (
            top not in neutrals and top_status != "avoid"
            and _color_chroma(top) >= config.get("accent_chroma", 0)
            and (dress or base in neutrals),
            f"{top_name} as the accent near the face",
        ),
        "wearable_palette": (
            rule.get("daily_saturation_fit", 1) if len(vivid) == len(colors) else 1,
            f"{pair} saturation for daily wear",
        ),
    }
    weights = config["weights"]
    fit = sum(checks[key][0] * weight for key, weight in weights.items()) / sum(weights.values())
    focus = max(weights, key=lambda key: weights[key] * (1 - checks[key][0]))
    reason = f"Good fit: {checks[focus][1]}." if fit == 1 else f"Less suited: {checks[focus][1]}."
    floor = config.get("minimum_fit", rule["minimum_fit"])
    return floor + (1 - floor) * fit, reason


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
    garment = "dress" if dress else "top"
    main = f"{_humanize(top)} {garment}"
    bottom = f"{_humanize(base)} bottom"
    top_value, base_value = _color_brightness(top), _color_brightness(base)
    top_chroma, base_chroma, shoes_chroma = map(_color_chroma, (top, base, shoes))
    components = []

    def add(rule_id: str, fit: float, reason: str) -> None:
        rule = rules[rule_id]
        maximum = float(rule.get("dress_max", rule["max"]) if dress else rule["max"])
        components.append(dict(id=rule_id, name=rule["name"], points=round(fit * maximum, 2),
                               max=maximum, reason=reason))

    top_name, base_name, shoe_name = map(str.title, (top, base, shoes))
    footwear = rules["footwear"]
    neutral_colors = footwear["anchor_colors"]
    face_contrast = abs(skin_value - top_value)
    face_rule = rules["face_value"]
    tolerance = face_rule["occasion_tolerance"].get(occasion, face_rule["tolerance"])
    fit, position = _range_fit(face_contrast, palette["face_value"], tolerance)
    direction = "lighter" if top_value > skin_value else "darker"
    relation = {"below": "close in lightness to", "within": f"{direction} than",
                "above": f"much {direction} than"}[position]
    add("face_value", fit, f"{top_name} {garment.lower()} is {relation} {skin_tone.replace('_', ' ')} skin.")

    if not dress:
        value_rule = rules["outfit_value"]
        bands = value_rule["occasion_bands"]
        low, high = bands.get(occasion, bands["daily"])
        high = max(high, value_rule["style_maximums"].get(style, high))
        if top in neutral_colors and base in neutral_colors:
            low, neutral_high = value_rule["neutral_pair_band"]
            high = max(high, neutral_high)
        fit, position = _range_fit(abs(top_value - base_value), [low, high], value_rule["tolerance"])
        relation = {"below": "low", "within": "balanced", "above": "high"}[position]
        add("outfit_value", fit, f"{top_name} top and {base_name} bottom create {relation} value contrast.")

    chroma = rules["chroma"]
    fit, position = _range_fit(top_chroma, palette["chroma"], chroma["tolerance"])
    chroma_text = {"below": "is softer than", "within": "matches", "above": "is more vivid than"}
    reason = f"{top_name} {garment.lower()} {chroma_text[position]} the {season.title()} palette."
    if not dress:
        base_fit, base_position = _range_fit(base_chroma, palette["chroma"], chroma["tolerance"])
        weight = chroma["secondary_weight"]
        if (1 - base_fit) * weight > (1 - fit) * (1 - weight):
            reason = f"{base_name} bottom {chroma_text[base_position]} the {season.title()} palette."
        fit = fit * (1 - weight) + base_fit * weight
    add("chroma", fit, reason)

    temperature = rules["temperature"]
    temperature_fit = temperature["fit"].get(undertone, temperature["fit"]["neutral"])
    top_temperature, base_temperature = map(_color_temperature, (top, base))
    weight = temperature["secondary_weight"] if not dress else 0
    fit = temperature_fit[top_temperature] * (1 - weight) + temperature_fit[base_temperature] * weight
    reason = f"{main} has a {top_temperature} temperature against a {undertone} undertone."
    if temperature_fit[base_temperature] < temperature_fit[top_temperature] and weight:
        reason = f"{bottom} has a {base_temperature} temperature against a {undertone} undertone."
    add("temperature", fit, reason)

    seasonal = rules["seasonal_palette"]
    avoid = palette["avoid"] + get_avoid_colors(undertone)
    top_status = _palette_status(top, palette["best"], avoid)
    base_status = _palette_status(base, palette["best"], avoid)
    weight = seasonal["secondary_weight"] if not dress else 0
    values = seasonal["fit"] | seasonal["season_fit"].get(season, {})
    if dress:
        values = values | seasonal["dress_fit"]
    fit = values[top_status] * (1 - weight) + values[base_status] * weight
    palette_name = season.title()
    if top_status == "avoid":
        reason = f"{main} is less flattering for {palette_name} coloring."
    elif base_status == "avoid":
        reason = f"{bottom} is less flattering for {palette_name} coloring."
    elif top_status == "best":
        reason = f"{main} matches the core {palette_name} palette."
    else:
        reason = f"{main} sits outside the core {palette_name} palette."
    add("seasonal_palette", fit, reason)

    harmony = _harmony(top, shoes if dress else base)
    proportion = rules["proportion"]
    vivid_threshold = proportion["competition_chroma"]
    pair_color, pair_name = (shoes, shoe_name) if dress else (base, base_name)
    pair_slot = "shoes" if dress else "bottom"
    pairing = f"{top_name} {garment.lower()} and {pair_name} {pair_slot}"
    harmony_reasons = {
        "monochromatic": "share a color family",
        "analogous": "are close on the color wheel",
        "complementary": "sit across the color wheel",
        "neutral-anchored": "form a neutral-anchored pair",
        "mixed": "mix hues from different color families",
    }
    harmony_key = harmony
    harmony_reason = f"{pairing} {harmony_reasons[harmony]}."
    if harmony == "monochromatic":
        if top in neutral_colors and pair_color in neutral_colors:
            harmony_key = "monochromatic_neutral"
        elif min(top_chroma, _color_chroma(pair_color)) >= vivid_threshold:
            harmony_key = "monochromatic_saturated"
            harmony_reason = f"{pairing} repeat a saturated hue."
    shares = proportion["dress_shares"] if dress else proportion["shares"]
    statement = style in footwear["statement_styles"]
    neutral_shoes = shoes in neutral_colors
    loud = not neutral_shoes and shoes_chroma >= max(top_chroma, base_chroma) + proportion["chroma_lead"]
    colors = (top, shoes) if dress else (top, base, shoes)
    vivid_hues = {_color_family(color) for color in colors
                 if color not in neutral_colors and _color_chroma(color) >= vivid_threshold}
    unanchored_brights = not any(color in neutral_colors for color in colors) and len(vivid_hues) > 1
    if unanchored_brights:
        harmony_key = "unanchored_brights"
        harmony_reason = f"{pairing} contribute to a mix of unanchored vivid hues."
    add("harmony", rules["harmony"]["fit"][harmony_key], harmony_reason)

    proportion_result, reason = "balanced", f"{top_name} {garment.lower()} leads the palette."
    if unanchored_brights:
        proportion_result, reason = "unanchored_brights", f"{pairing} lack a neutral to balance the vivid palette."
    elif loud and not statement and shares["shoes"] <= proportion["max_accent_share"]:
        proportion_result, reason = "dominant_shoes", f"{shoe_name} shoes draw focus from the {top} {garment.lower()}."
    elif harmony_key == "monochromatic_saturated" and shoes == top:
        proportion_result, reason = "unanchored_brights", f"{top_name} spans every slot at full saturation."
    elif (
        not dress
        and top not in neutral_colors and base not in neutral_colors
        and min(top_chroma, base_chroma) >= vivid_threshold
        and min(shares["top"], shares["bottom"]) > proportion["max_accent_share"]
    ):
        proportion_result, reason = "competing_garments", f"{pairing} occupy large areas of vivid color."
    elif loud:
        reason = f"{shoe_name} shoes add a small statement accent."
    add("proportion", proportion["fit"][proportion_result], reason)

    for rule_id, profile in (
        ("style_fit", STYLE_RULES.get(style, STYLE_RULES["casual"])),
        ("dress_code", OCCASION_RULES.get(occasion, OCCASION_RULES["daily"])),
    ):
        fit, reason = _profile_color_fit(
            profile, rules[rule_id], top, base, shoes, dress, skin_value, top_status
        )
        add(rule_id, fit, reason)

    base_slot = "dress" if dress else "bottom"
    if shoes == base or neutral_shoes:
        level, reason = "anchored", f"{shoe_name} shoes anchor the {base} {base_slot}."
    elif loud and not statement:
        level, reason = "loud", f"{shoe_name} shoes are more vivid than the {top} {garment.lower()}."
    elif loud:
        level, reason = "statement", f"{shoe_name} shoes add a streetwear accent."
    else:
        level, reason = "unanchored", f"{shoe_name} shoes introduce a separate accent color."
    add("footwear", footwear["fit"][level], reason)

    score = round(sum(component["points"] for component in components))
    label = next(label for floor, label in sorted(SCORING_RULES["labels"].items(), key=lambda item: int(item[0]), reverse=True) if score >= int(floor))
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
    style_colors = profile["style"].get("preferred_colors", [])
    style_scoring = profile["style"].get("scoring", {})
    style_bases = style_scoring.get("bases", [])
    top_candidates = [
        color for color in dict.fromkeys(recommended[:10] + palette["best"] + style_colors + style_bases)
        if color in ALL_COLORS
    ]
    pant_candidates = [
        color
        for color in dict.fromkeys(
            profile["undertone"].get("recommended_neutrals", [])
            + style_colors
            + style_bases
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
    vivid_count = style_scoring.get("suggestion_vivid_count")
    threshold = SCORING_RULES["rules"]["proportion"]["competition_chroma"]
    if vivid_count is not None:
        shoe_candidates = profile["style"]["preferred_shoes"]
    for shirt_color, pants_color, shoes_color in product(top_candidates, pant_candidates, shoe_candidates):
        if vivid_count is not None:
            garments = (shirt_color, pants_color)
            if sum(_color_chroma(color) >= threshold for color in garments) != vivid_count:
                continue
            if any(_color_chroma(color) < threshold and color not in style_scoring["bases"] for color in garments):
                continue
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

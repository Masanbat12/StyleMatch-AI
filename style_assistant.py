from __future__ import annotations

from typing import List

from knowledge_base import GROUNDED_RULES, OCCASION_RULES, SOURCES, STYLE_RULES
from recommendation_engine import generate_outfit_suggestions


def build_grounded_answer(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    user_prompt: str,
) -> str:
    best_colors = GROUNDED_RULES.get(undertone, {}).get("best", [])
    avoid_colors = GROUNDED_RULES.get(undertone, {}).get("avoid", [])
    undertone_advice = GROUNDED_RULES.get(undertone, {}).get("advice", "")
    style_colors = STYLE_RULES.get(style, [])
    occasion_colors = OCCASION_RULES.get(occasion, [])

    suggestions = generate_outfit_suggestions(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        limit=3,
    )

    lines: List[str] = []
    lines.append("Grounded style recommendation")
    lines.append("")
    lines.append(f"Your profile: skin tone = {skin_tone}, undertone = {undertone}, style = {style}, occasion = {occasion}.")
    lines.append(f"Question: {user_prompt.strip() or 'General styling advice'}")
    lines.append("")
    lines.append("What the assistant is using:")
    lines.append(f"- Undertone guidance: {undertone_advice}")
    lines.append(f"- Best color zone: {', '.join(best_colors[:7]) if best_colors else 'N/A'}")
    lines.append(f"- Style-friendly colors: {', '.join(style_colors[:5]) if style_colors else 'N/A'}")
    lines.append(f"- Occasion-friendly colors: {', '.join(occasion_colors[:5]) if occasion_colors else 'N/A'}")
    if avoid_colors:
        lines.append(f"- Lower-priority colors: {', '.join(avoid_colors)}")
    lines.append("")
    lines.append("Top outfit suggestions:")
    for i, outfit in enumerate(suggestions, start=1):
        lines.append(
            f"{i}. Shirt: {outfit['shirt_color']}, Pants: {outfit['pants_color']}, Shoes: {outfit['shoes_color']} "
            f"(score: {outfit['score']}/100)"
        )
    lines.append("")
    lines.append("Sources baked into this project:")
    for source in SOURCES:
        lines.append(f"- {source['title']}: {source['url']}")
    return "\n".join(lines)

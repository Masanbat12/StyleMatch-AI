from __future__ import annotations

from typing import List

from knowledge_base import OCCASION_RULES, SOURCES, STYLE_RULES, UNDERTONE_RULES
from models import UserProfile
from recommendation_engine import generate_outfit_suggestions


def _humanize(value: str) -> str:
    return value.replace("_", " ").title()


def build_grounded_answer(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    user_prompt: str,
    user_context: dict | None = None,
) -> str:
    profile = UserProfile(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
    )
    undertone_data = UNDERTONE_RULES.get(undertone, {})
    style_data = STYLE_RULES.get(style, {})
    occasion_data = OCCASION_RULES.get(occasion, {})

    suggestions = generate_outfit_suggestions(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        limit=3,
        user_context=user_context,
    )

    lines: List[str] = []
    lines.append("StyleMatch AI guidance")
    lines.append("")
    lines.append(
        "Your profile: "
        f"skin tone = {_humanize(profile.skin_tone)}, undertone = {_humanize(profile.undertone)}, "
        f"style = {_humanize(profile.style)}, occasion = {_humanize(profile.occasion)}."
    )
    lines.append(f"Question: {user_prompt.strip() or 'General styling advice'}")
    lines.append("")
    lines.append("What the assistant is using:")
    for note in undertone_data.get("notes", [])[:2]:
        lines.append(f"- Undertone note: {note}")
    for note in style_data.get("fit_notes", [])[:2]:
        lines.append(f"- Style note: {note}")
    for note in occasion_data.get("notes", [])[:2]:
        lines.append(f"- Occasion note: {note}")
    if user_context:
        insights = user_context.get("insights", {})
        if insights.get("top_colors"):
            lines.append(f"- Learned preference: you often keep {', '.join(insights['top_colors'][:3])} tones.")
        if insights.get("top_styles"):
            lines.append(f"- Learned style signal: {', '.join(insights['top_styles'][:2])}.")
    lines.append("")
    lines.append("Best outfit directions right now:")
    for i, outfit in enumerate(suggestions, start=1):
        lines.append(
            f"{i}. Shirt: {_humanize(outfit['shirt_color'])}, Pants: {_humanize(outfit['pants_color'])}, Shoes: {_humanize(outfit['shoes_color'])} "
            f"(score: {outfit['score']}/100)"
        )
        lines.append(f"   Why it works: {outfit['explanation']}")
        for reason in outfit.get("reasons", [])[:2]:
            lines.append(f"   - {reason}")
    lines.append("")
    lines.append("Embedded project sources:")
    for source in SOURCES:
        lines.append(f"- {source['title']}: {source['url']}")
    return "\n".join(lines)

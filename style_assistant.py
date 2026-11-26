from __future__ import annotations

from typing import Any, Iterator, List

import recommendation_engine
from knowledge_base import OCCASION_RULES, SOURCES, STYLE_RULES, UNDERTONE_RULES
from models import UserProfile
from recommendation_engine import (
    generate_dress_suggestions,
    generate_outfit_suggestions,
    get_avoid_colors,
    get_recommended_colors,
)

MAX_QUESTION_CHARS = 600

SYSTEM_PROMPT = """You are StyleMatch AI, a professional personal stylist and colour analyst.
You advise one person about outfits, using ONLY the facts in the STYLE FACTS block of the
user message: their profile, the project's colour rules, the outfit score computed by the
StyleMatch scoring engine, and the engine's top-ranked looks.

How to answer:
- Reply in the same language as the person's question (Hebrew question -> Hebrew answer).
- Open with a one-sentence direct answer to the question.
- Then give two or three concrete outfit options, each as: garment colours, and one short
  reason tied to a fact (undertone, contrast with their skin tone, colour harmony, occasion).
  Prefer the engine's top-ranked looks; you may adapt them, but only with colours from the
  recommended palette or the listed looks.
- If a current outfit is given, assess it using the engine's score and reasons, then say the
  single change that would most improve it.
- End with one line: what to avoid, taken from the lower-priority colours.
- Scores are computed by the engine. Quote them as given; never invent, re-calculate or
  change a score, and never give a score for an outfit the facts do not score.
- If the question is not about clothing, colour or style, say briefly that you only help with
  outfits and offer one relevant suggestion instead.
- Use the garment names given in the facts (shirt, hoodie, jacket, dress, pants, skirt).
- Plain, warm, professional tone. No headings, no emojis. At most 180 words."""


def _bullet_lines(items: list[str], prefix: str = "- ") -> list[str]:
    return [f"{prefix}{item}" for item in items if item]


def build_style_facts(
    *,
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    top_label: str = "Shirt",
    bottom_label: str = "Pants",
    is_dress: bool = False,
    current_outfit: dict[str, Any] | None = None,
) -> str:
    """Assemble the grounded fact sheet the LLM is allowed to use."""
    undertone_data = UNDERTONE_RULES.get(undertone, {})
    style_data = STYLE_RULES.get(style, {})
    occasion_data = OCCASION_RULES.get(occasion, {})
    recommended = get_recommended_colors(undertone, style, occasion)
    avoided = get_avoid_colors(undertone)

    generator = generate_dress_suggestions if is_dress else generate_outfit_suggestions
    looks = generator(skin_tone=skin_tone, undertone=undertone, style=style, occasion=occasion, limit=3)

    lines: list[str] = [
        "PROFILE",
        f"- Skin tone: {_humanize(skin_tone)}; undertone: {_humanize(undertone)}",
        f"- Style: {_humanize(style)}; occasion: {_humanize(occasion)}",
        f"- Garments: {'one-piece ' + top_label.lower() if is_dress else top_label.lower() + ' + ' + bottom_label.lower()} + shoes",
        "",
        "COLOUR RULES",
        f"- Recommended palette: {', '.join(_humanize(c) for c in recommended)}",
        f"- Lower-priority colours: {', '.join(_humanize(c) for c in avoided) or 'none'}",
    ]
    lines += _bullet_lines(undertone_data.get("notes", [])[:3], "- Undertone: ")
    lines += _bullet_lines(style_data.get("fit_notes", [])[:3], "- Style: ")
    lines += _bullet_lines(occasion_data.get("notes", [])[:3], "- Occasion: ")

    lines += ["", "ENGINE TOP-RANKED LOOKS"]
    for index, look in enumerate(looks, start=1):
        if is_dress:
            garments = f"{top_label} {_humanize(look['shirt_color'])}, shoes {_humanize(look['shoes_color'])}"
        else:
            garments = (
                f"{top_label} {_humanize(look['shirt_color'])}, {bottom_label.lower()} "
                f"{_humanize(look['pants_color'])}, shoes {_humanize(look['shoes_color'])}"
            )
        lines.append(f"{index}. {garments} — score {look['score']}/100. {look.get('explanation', '')}")

    if current_outfit:
        lines += ["", "CURRENT OUTFIT IN THE BUILDER"]
        if is_dress:
            lines.append(
                f"- {top_label} {_humanize(current_outfit['shirt_color'])}, shoes {_humanize(current_outfit['shoes_color'])}"
            )
        else:
            lines.append(
                f"- {top_label} {_humanize(current_outfit['shirt_color'])}, {bottom_label.lower()} "
                f"{_humanize(current_outfit['pants_color'])}, shoes {_humanize(current_outfit['shoes_color'])}"
            )
        lines.append(f"- Engine score: {current_outfit['score']}/100")
        report_fn = getattr(recommendation_engine, "score_report", None)
        report = None
        if callable(report_fn):
            try:
                report = report_fn(
                    skin_tone, undertone, style, occasion,
                    current_outfit["shirt_color"], current_outfit["pants_color"], current_outfit["shoes_color"],
                    dress=is_dress,
                )
            except Exception:
                report = None
        if report:
            if report.get("season"):
                lines.append(f"- Colour season: {report['season']}")
            lines += _bullet_lines(list(report.get("strengths", []))[:4], "- Strength: ")
            lines += _bullet_lines(list(report.get("risks", []))[:4], "- Risk: ")
        else:
            lines += _bullet_lines(list(current_outfit.get("reasons", []))[:6], "- Engine reason: ")

    return "\n".join(lines)


def build_llm_messages(user_prompt: str, style_facts: str) -> list[dict[str, str]]:
    question = (user_prompt or "").strip()[:MAX_QUESTION_CHARS] or "What should I wear for this occasion?"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"STYLE FACTS\n{style_facts}\n\nQUESTION FROM THE PERSON\n{question}",
        },
    ]


def stream_llm_answer(user_prompt: str, style_facts: str) -> Iterator[str]:
    """Stream a grounded LLM answer. Raises llm_client.LLMUnavailableError on failure."""
    from llm_client import stream_chat

    yield from stream_chat(build_llm_messages(user_prompt, style_facts))


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

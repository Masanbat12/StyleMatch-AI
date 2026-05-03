from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SOURCES = [
    {
        "title": "Canva Color Wheel",
        "url": "https://www.canva.com/colors/color-wheel/",
        "summary": "Complementary colors sit opposite each other and create high contrast; analogous colors sit next to each other and feel harmonious.",
    },
    {
        "title": "Adobe Color Theory",
        "url": "https://www.adobe.com/il_en/creativecloud/design/discover/secondary-colors.html",
        "summary": "Analogous colors are neighboring colors on the wheel; contrast is important when combining them.",
    },
    {
        "title": "The Concept Wardrobe - What is Color Analysis",
        "url": "https://theconceptwardrobe.com/colour-analysis-comprehensive-guides/what-is-color-analysis",
        "summary": "Warm colors have yellow undertones while cool colors have blue undertones.",
    },
    {
        "title": "The Concept Wardrobe - Which Season Are You?",
        "url": "https://theconceptwardrobe.com/colour-analysis-comprehensive-guides/seasonal-color-analysis-which-color-season-are-you",
        "summary": "Skin undertones can be broadly grouped into warm, cool, and neutral for color analysis.",
    },
    {
        "title": "OpenCV Colorspaces Tutorial",
        "url": "https://docs.opencv.org/3.4/df/d9d/tutorial_py_colorspaces.html",
        "summary": "OpenCV supports color space conversion such as BGR to HSV and BGR to YCrCb, which helps with color-based image processing.",
    },
]

STYLE_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "style_knowledge"


def _load_json(filename: str) -> dict[str, Any]:
    with (STYLE_KNOWLEDGE_DIR / filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)


COLOR_THEORY_RULES = _load_json("color_theory_rules.json")
UNDERTONE_RULES = _load_json("undertone_rules.json")
STYLE_RULES = _load_json("style_rules.json")
OCCASION_RULES = _load_json("occasion_rules.json")
COLOR_METADATA = _load_json("color_metadata.json")
EXPLANATION_TEMPLATES = _load_json("explanation_templates.json")

# Legacy compatibility for modules that still expect the older shape.
GROUNDED_RULES = {
    undertone: {
        "best": data["best_colors"],
        "avoid": data["avoid_colors"],
        "advice": " ".join(data["notes"]),
    }
    for undertone, data in UNDERTONE_RULES.items()
}

from __future__ import annotations

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

GROUNDED_RULES = {
    "warm": {
        "best": ["olive", "beige", "cream", "camel", "brown", "forest green", "rust", "mustard"],
        "avoid": ["icy blue", "neon purple"],
        "advice": "Warm undertones usually look stronger in earthy, golden, and muted-warm palettes.",
    },
    "cool": {
        "best": ["navy", "charcoal", "white", "burgundy", "cobalt", "gray", "icy blue", "deep green"],
        "avoid": ["mustard", "orange-yellow"],
        "advice": "Cool undertones usually work better with blue-based and crisp, cooler shades.",
    },
    "neutral": {
        "best": ["taupe", "white", "black", "blue", "green", "soft pink", "gray", "beige"],
        "avoid": ["extreme neon green"],
        "advice": "Neutral undertones can flex across both warm and cool ranges, especially balanced mid-saturation colors.",
    },
}

STYLE_RULES = {
    "casual": ["white", "blue", "olive", "gray", "beige"],
    "elegant": ["black", "burgundy", "navy", "camel", "charcoal"],
    "street": ["red", "cobalt", "black", "forest green"],
    "minimal": ["white", "black", "gray", "taupe", "beige"],
}

OCCASION_RULES = {
    "daily": ["white", "blue", "gray", "olive"],
    "date": ["burgundy", "black", "navy", "deep green"],
    "work": ["navy", "gray", "white", "charcoal"],
    "evening": ["black", "burgundy", "deep green", "charcoal"],
}

from __future__ import annotations

from typing import Final

ALL_COLORS: Final[list[str]] = [
    "white",
    "black",
    "gray",
    "blue",
    "navy",
    "olive",
    "beige",
    "cream",
    "brown",
    "rust",
    "mustard",
    "forest green",
    "burgundy",
    "icy blue",
    "taupe",
    "green",
    "soft pink",
    "red",
    "cobalt",
    "charcoal",
    "camel",
    "deep green",
]

COLOR_MAP: Final[dict[str, str]] = {
    "white": "#FFFFFF",
    "black": "#1A1A1A",
    "gray": "#808080",
    "blue": "#3498DB",
    "navy": "#000080",
    "olive": "#556B2F",
    "beige": "#F5F5DC",
    "cream": "#FFFDD0",
    "brown": "#8B4513",
    "rust": "#B7410E",
    "mustard": "#E1AD01",
    "forest green": "#228B22",
    "burgundy": "#800020",
    "icy blue": "#AFDBF5",
    "taupe": "#483C32",
    "green": "#27AE60",
    "soft pink": "#FFB6C1",
    "red": "#E74C3C",
    "cobalt": "#0047AB",
    "charcoal": "#36454F",
    "camel": "#C19A6B",
    "deep green": "#056608",
}

COLOR_BRIGHTNESS: Final[dict[str, int]] = {
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

SKIN_TONE_MAP: Final[dict[str, str]] = {
    "very_fair": "#FDF0E9",
    "fair": "#FFDBAC",
    "light": "#F1C27D",
    "light_medium": "#E0AC69",
    "medium": "#C68642",
    "tan": "#8D5524",
    "deep_tan": "#6A4128",
    "dark": "#4B2C20",
    "deep_dark": "#2E1A12",
}

SKIN_BRIGHTNESS: Final[dict[str, int]] = {
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

SKIN_TONE_OPTIONS: Final[list[str]] = list(SKIN_BRIGHTNESS.keys())
UNDERTONE_OPTIONS: Final[list[str]] = ["warm", "cool", "neutral"]
STYLE_OPTIONS: Final[list[str]] = ["casual", "elegant", "street", "minimal"]
OCCASION_OPTIONS: Final[list[str]] = ["daily", "date", "work", "evening"]
NEUTRAL_SHOE_COLORS: Final[set[str]] = {"white", "black", "brown", "beige"}
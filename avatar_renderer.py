from __future__ import annotations

from PIL import Image, ImageDraw

COLOR_MAP = {
    "white": "#F5F5F5",
    "black": "#1F1F1F",
    "gray": "#808080",
    "blue": "#3B82F6",
    "navy": "#1E3A8A",
    "olive": "#708238",
    "beige": "#D6C6A8",
    "cream": "#FFF5D6",
    "brown": "#7A5230",
    "rust": "#B7410E",
    "mustard": "#D4A017",
    "forest green": "#1B5E20",
    "burgundy": "#800020",
    "icy blue": "#A5D8FF",
    "taupe": "#8B8589",
    "green": "#22A45D",
    "soft pink": "#F2B6C6",
    "red": "#D62828",
    "cobalt": "#0047AB",
    "charcoal": "#36454F",
    "camel": "#C19A6B",
    "deep green": "#0B6E4F",
}

SKIN_TONE_MAP = {
    "very_fair": "#F8E1D4",
    "fair": "#F1D0BC",
    "light": "#E4BC9A",
    "light_medium": "#D4A176",
    "medium": "#BC7A4A",
    "tan": "#9F603A",
    "deep_tan": "#7E4C2E",
    "dark": "#5D3923",
    "deep_dark": "#3F2517",
}


def resolve_color(name: str, fallback: str = "#999999") -> str:
    return COLOR_MAP.get(name.lower(), fallback)


def render_avatar(
    skin_tone: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    width: int = 420,
    height: int = 620,
) -> Image.Image:
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    skin = SKIN_TONE_MAP.get(skin_tone, "#BC7A4A")
    shirt = resolve_color(shirt_color)
    pants = resolve_color(pants_color)
    shoes = resolve_color(shoes_color)

    draw.rounded_rectangle((35, 35, width - 35, height - 35), radius=28, outline="#CBD5E1", width=2)
    draw.ellipse((150, 45, 270, 165), fill=skin, outline="#222222", width=2)
    draw.rounded_rectangle((190, 160, 230, 195), radius=8, fill=skin, outline="#222222", width=2)
    draw.rounded_rectangle((110, 195, 310, 380), radius=26, fill=shirt, outline="#222222", width=2)
    draw.polygon([(110, 210), (60, 260), (95, 340), (130, 250)], fill=shirt, outline="#222222")
    draw.polygon([(310, 210), (360, 260), (325, 340), (290, 250)], fill=shirt, outline="#222222")
    draw.rounded_rectangle((58, 260, 92, 382), radius=10, fill=skin, outline="#222222", width=2)
    draw.rounded_rectangle((328, 260, 362, 382), radius=10, fill=skin, outline="#222222", width=2)
    draw.rounded_rectangle((135, 380, 205, 545), radius=16, fill=pants, outline="#222222", width=2)
    draw.rounded_rectangle((215, 380, 285, 545), radius=16, fill=pants, outline="#222222", width=2)
    draw.rounded_rectangle((122, 540, 210, 580), radius=12, fill=shoes, outline="#222222", width=2)
    draw.rounded_rectangle((210, 540, 298, 580), radius=12, fill=shoes, outline="#222222", width=2)
    draw.text((52, 14), "StyleMatch AI Avatar Preview", fill="#111827")
    return image

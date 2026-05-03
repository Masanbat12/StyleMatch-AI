from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps

from catalog import COLOR_MAP, SKIN_TONE_MAP

ASSETS_DIR = Path(__file__).resolve().parent / "avatar_assets"


@dataclass(frozen=True)
class Placement:
    x: int
    y: int
    scale: float = 1.0


AVATAR_PLACEMENT = {
    "shirt": Placement(x=137, y=84, scale=1.04),
    "pants": Placement(x=169, y=216, scale=1.02),
    "shoes": Placement(x=153, y=466, scale=1.02),
}

SHOE_PAIR_GAP = 77
RIGHT_SHOE_Y_OFFSET = -2


def resolve_color(color_name: str, fallback: str = "#808080") -> tuple[int, int, int]:
    hex_value = COLOR_MAP.get(str(color_name).lower(), fallback)
    try:
        return ImageColor.getrgb(hex_value)
    except ValueError:
        return ImageColor.getrgb(fallback)


def resolve_skin_tone(tone_name: str, fallback: str = "#A0A0A0") -> tuple[int, int, int]:
    hex_value = SKIN_TONE_MAP.get(str(tone_name).lower(), fallback)
    try:
        return ImageColor.getrgb(hex_value)
    except ValueError:
        return ImageColor.getrgb(fallback)


def load_rgba(name: str) -> Image.Image:
    path = ASSETS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing asset: {name} in {ASSETS_DIR}")
    return Image.open(path).convert("RGBA")


def load_first_available(*names: str) -> Image.Image:
    for name in names:
        path = ASSETS_DIR / name
        if path.exists():
            return Image.open(path).convert("RGBA")
    raise FileNotFoundError(f"Missing asset. Tried: {', '.join(names)} in {ASSETS_DIR}")


def alpha_bbox(image: Image.Image, threshold: int = 10) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > threshold else 0).getbbox()
    if bbox is None:
        return (0, 0, image.width, image.height)
    return bbox


def crop_visible_content(image: Image.Image, threshold: int = 10) -> Image.Image:
    return image.crop(alpha_bbox(image, threshold))


def tint_layer(overlay: Image.Image, color_rgb: tuple[int, int, int]) -> Image.Image:
    gray = overlay.convert("L")
    colored = ImageOps.colorize(gray, black="#080808", white=color_rgb).convert("RGBA")
    colored.putalpha(overlay.getchannel("A"))
    return colored


def place_layer(
    layer: Image.Image,
    target_size: tuple[int, int],
    placement: Placement,
    offset: tuple[int, int] = (0, 0),
) -> Image.Image:
    cropped = crop_visible_content(layer)
    if placement.scale != 1.0:
        cropped = cropped.resize(
            (
                max(1, round(cropped.width * placement.scale)),
                max(1, round(cropped.height * placement.scale)),
            ),
            Image.Resampling.LANCZOS,
        )

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    canvas.alpha_composite(cropped, (placement.x + offset[0], placement.y + offset[1]))
    return canvas


def build_skin_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    draw.ellipse((170, 19, 279, 117), fill=255)
    draw.rounded_rectangle((196, 96, 251, 136), radius=10, fill=255)

    draw.rounded_rectangle((138, 114, 171, 303), radius=14, fill=255)
    draw.rounded_rectangle((278, 114, 311, 303), radius=14, fill=255)

    draw.ellipse((134, 282, 174, 367), fill=255)
    draw.ellipse((275, 282, 315, 367), fill=255)

    return mask


def build_skin_layer(base: Image.Image, skin_tone: str) -> Image.Image:
    tinted_base = tint_layer(base, resolve_skin_tone(skin_tone))
    skin_mask = build_skin_mask(base.size)
    combined_alpha = ImageChops.multiply(base.getchannel("A"), skin_mask)
    tinted_base.putalpha(combined_alpha)
    return tinted_base


def render_avatar(
    skin_tone: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    width: int = 420,
    height: int = 620,
) -> Image.Image:
    base = load_rgba("default_avatar.png")
    shirt_overlay = load_rgba("shirt_overlay.png")
    pants_overlay = load_rgba("pants_overlay.png")
    left_shoe_overlay = load_first_available("l_shoe_overlay.png", "l_shoes_overlay.png")
    right_shoe_overlay = load_first_available("r_shoes_overlay.png", "r_shoe_overlay.png")

    target_size = base.size
    skin_layer = build_skin_layer(base, skin_tone)

    shirt_layer = place_layer(
        tint_layer(shirt_overlay, resolve_color(shirt_color)),
        target_size,
        AVATAR_PLACEMENT["shirt"],
    )
    pants_layer = place_layer(
        tint_layer(pants_overlay, resolve_color(pants_color)),
        target_size,
        AVATAR_PLACEMENT["pants"],
    )
    left_shoe_layer = place_layer(
        tint_layer(left_shoe_overlay, resolve_color(shoes_color)),
        target_size,
        AVATAR_PLACEMENT["shoes"],
    )
    right_shoe_layer = place_layer(
        tint_layer(right_shoe_overlay, resolve_color(shoes_color)),
        target_size,
        AVATAR_PLACEMENT["shoes"],
        offset=(SHOE_PAIR_GAP, RIGHT_SHOE_Y_OFFSET),
    )

    output = Image.new("RGBA", target_size, (0, 0, 0, 0))
    output = Image.alpha_composite(output, skin_layer)
    output = Image.alpha_composite(output, left_shoe_layer)
    output = Image.alpha_composite(output, right_shoe_layer)
    output = Image.alpha_composite(output, pants_layer)
    output = Image.alpha_composite(output, shirt_layer)
    return output.resize((width, height), Image.Resampling.LANCZOS)

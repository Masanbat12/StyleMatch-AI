from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import math

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps

from catalog import COLOR_MAP, SKIN_TONE_MAP
from avatar_materials import recolor_material

ASSETS_DIR = Path(__file__).resolve().parent / "avatar_assets"


@dataclass(frozen=True)
class Placement:
    x: int
    y: int
    scale: float = 1.0


AVATAR_PLACEMENT = {
    "shirt": Placement(x=137, y=84, scale=1.04),
    "pants": Placement(x=169, y=216, scale=1.02),
    "shoes": Placement(x=147, y=475, scale=0.90),
}

SHOE_PAIR_GAP = 93
RIGHT_SHOE_Y_OFFSET = -1


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


@lru_cache(maxsize=32)
def load_rgba(name: str) -> Image.Image:
    path = ASSETS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing asset: {name} in {ASSETS_DIR}")
    with Image.open(path) as image:
        return image.convert("RGBA")


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


def tint_layer(overlay: Image.Image, color_rgb: tuple[int, int, int], *, material: str = "fabric") -> Image.Image:
    if material != "skin":
        return recolor_material(overlay, color_rgb, material)
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

    draw.rounded_rectangle((138, 114, 171, 284), radius=14, fill=255)
    draw.rounded_rectangle((278, 114, 311, 284), radius=14, fill=255)

    draw.ellipse((134, 277, 168, 326), fill=255)
    draw.ellipse((281, 277, 315, 326), fill=255)

    return mask


def build_skin_layer(base: Image.Image, skin_tone: str) -> Image.Image:
    tinted_base = tint_layer(base, resolve_skin_tone(skin_tone), material="skin")
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
    avatar_model: str = "male",
    shoe_style: str = "sneakers",
    top_style: str = "shirt",
    bottom_style: str | None = None,
    outerwear_color: str = "charcoal",
) -> Image.Image:
    if width <= 0 or height <= 0:
        raise ValueError("Avatar dimensions must be positive.")
    if avatar_model not in {"male", "female"}:
        raise ValueError("Unknown avatar model.")
    if top_style not in ({"shirt", "hoodie", "jacket", "dress"} if avatar_model == "female" else {"shirt", "hoodie", "jacket"}):
        raise ValueError("Unknown top style.")
    bottom_style = "dress" if top_style == "dress" else bottom_style
    bottom_style = bottom_style or ("skirt" if avatar_model == "female" else "pants")
    if bottom_style not in ({"skirt", "pants", "dress"} if avatar_model == "female" else {"pants"}):
        raise ValueError("Unsupported bottom style for this avatar.")
    if avatar_model == "female":
        return _render_female(skin_tone, shirt_color, pants_color, shoes_color,
                              width, height, shoe_style, top_style, bottom_style, outerwear_color)
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
        tint_layer(pants_overlay, resolve_color(pants_color), material="denim"),
        target_size,
        AVATAR_PLACEMENT["pants"],
    )
    left_shoe_layer = place_layer(
        tint_layer(left_shoe_overlay, resolve_color(shoes_color), material="shoes"),
        target_size,
        AVATAR_PLACEMENT["shoes"],
    )
    right_shoe_layer = place_layer(
        tint_layer(right_shoe_overlay, resolve_color(shoes_color), material="shoes"),
        target_size,
        AVATAR_PLACEMENT["shoes"],
        offset=(SHOE_PAIR_GAP, RIGHT_SHOE_Y_OFFSET),
    )

    output = Image.new("RGBA", target_size, (0, 0, 0, 0))
    output = Image.alpha_composite(output, skin_layer)
    output = Image.alpha_composite(output, left_shoe_layer)
    output = Image.alpha_composite(output, right_shoe_layer)
    output = Image.alpha_composite(output, pants_layer)
    if top_style == "shirt":
        output = Image.alpha_composite(output, shirt_layer)
    else:
        if top_style == "jacket":
            output = Image.alpha_composite(output, _jacket_undershirt(shirt_layer, (185, 84, 263, 284)))
        outer = _fitted_garment(f"man_{top_style}.png", MALE_OUTER_FIT[top_style],
                                outerwear_color if top_style == "jacket" else shirt_color)
        output = Image.alpha_composite(output, outer)
    return _fit_output(output, width, height)


# Coordinates refer to the same 448 x 557 canvas as the male assets.
# Each garment is sized independently to the female body's shoulders, waist and feet.
FEMALE_FIT = {
    "body": (152, 16, 144, 515),
    "shirt": (154, 91, 140, 156),
    "skirt": (142, 214, 164, 233),
    "pants": (180, 214, 88, 287),
    "dress": (151, 91, 146, 348),
    "hoodie": (147, 82, 154, 199),
    "jacket": (144, 80, 160, 203),

}


MALE_OUTER_FIT = {"hoodie": (133, 81, 182, 205), "jacket": (132, 77, 184, 209)}


def _jacket_undershirt(layer: Image.Image, torso: tuple[int, int, int, int]) -> Image.Image:
    # A short sleeve shirt must not protrude through a jacket's shoulders.
    clipped = Image.new("RGBA", layer.size)
    clipped.paste(layer.crop(torso), torso[:2])
    return clipped


def _fitted_garment(name: str, fit: tuple[int, int, int, int], color: str) -> Image.Image:
    image = load_rgba(name).copy()
    image = image.crop(alpha_bbox(image, threshold=128))
    image.putalpha(image.getchannel("A").point(lambda value: 0 if value < 20 else value))
    x, y, width, height = fit
    image = tint_layer(image, resolve_color(color), material="jacket" if "jacket" in name else "fabric")
    if "hoodie" in name:
        # Fit the hood to the neck separately from the long sleeves: scaling the
        # whole sprite uniformly either exposes shoulders or covers the face.
        split = round(image.height * 0.20)
        hood_height = round(height * 0.12)
        layer = Image.new("RGBA", (width, height))
        layer.alpha_composite(image.crop((0, 0, image.width, split)).resize(
            (width, hood_height), Image.Resampling.LANCZOS))
        layer.alpha_composite(image.crop((0, split, image.width, image.height)).resize(
            (width, height - hood_height), Image.Resampling.LANCZOS), (0, hood_height))
    else:
        layer = image.resize((width, height), Image.Resampling.LANCZOS)
    if "jacket" in name:
        # The supplied PNGs include an opaque lining in the jacket opening.
        # Cut that opening out so the actual shirt (and pants below its hem)
        # remain visible while the lapels and sleeves stay in front.
        points = ([(0.43, 0.0), (0.58, 0.0), (0.59, 0.13), (0.55, 0.40),
                   (0.55, 0.72), (0.59, 1.0), (0.43, 1.0), (0.46, 0.72),
                   (0.46, 0.40), (0.40, 0.13)] if name.startswith("man_") else
                  [(0.43, 0.0), (0.58, 0.0), (0.60, 0.14), (0.55, 0.42),
                   (0.56, 0.72), (0.60, 1.0), (0.43, 1.0), (0.47, 0.72),
                   (0.47, 0.42), (0.40, 0.14)])
        mask = Image.new("L", (width * 4, height * 4))
        ImageDraw.Draw(mask).polygon([(round(px * width * 4), round(py * height * 4))
                                     for px, py in points], fill=255)
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), ImageOps.invert(mask)))
    canvas = Image.new("RGBA", (448, 557))
    canvas.alpha_composite(layer, (x, y))
    return canvas


def _fit_output(output: Image.Image, width: int, height: int) -> Image.Image:
    # Transparent letterboxing preserves anatomy at every preview aspect ratio.
    fitted = ImageOps.contain(output, (width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height))
    canvas.alpha_composite(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return canvas


def _female_asset(name: str) -> Image.Image:
    image = load_rgba(f"girl cloths/{name}").copy()
    # The supplied body has faint alpha across its entire square canvas.
    # Ignore that padding when finding its anatomical bounds.
    image = image.crop(alpha_bbox(image, threshold=128))
    image.putalpha(image.getchannel("A").point(lambda value: 0 if value < 20 else value))
    return image


# Position each shoe by the ankle opening, not the edge of its transparent box.
FEMALE_ANKLES = {"left": (208, 497, -12), "right": (240, 497, 9)}


def _female_shoe_layer(side: str, shoe_style: str, color: str) -> Image.Image:
    filename = ({"left": "girl_l_shoe.png", "right": "girl_r_shoe.png"} if shoe_style == "sneakers"
                else {"left": "l_heel.png", "right": "r_heel.png"})[side]
    ankle_x, ankle_y, angle = FEMALE_ANKLES[side]
    scale = 4
    width, height = 28, 43
    shoe = tint_layer(_female_asset(filename), resolve_color(color), material="shoes")
    shoe = shoe.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
    rotated = shoe.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    # Shoe openings are centered horizontally, 17% down the source image.
    radians = math.radians(angle)
    dy = shoe.height * (0.17 - 0.5)
    anchor_x = (rotated.width / 2 + math.sin(radians) * dy) / scale
    anchor_y = (rotated.height / 2 + math.cos(radians) * dy) / scale
    rotated = rotated.resize((round(rotated.width / scale), round(rotated.height / scale)),
                             Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (448, 557))
    canvas.alpha_composite(rotated, (round(ankle_x - anchor_x), round(ankle_y - anchor_y)))
    return canvas


def _render_female(skin_tone, shirt_color, skirt_color, shoes_color, width, height, shoe_style,
                   top_style, bottom_style, outerwear_color):
    if shoe_style not in {"sneakers", "heels"}:
        raise ValueError("Unknown female shoe style.")
    output = Image.new("RGBA", (448, 557))

    def add(name, fit_key, color, material="fabric"):
        x, y, w, h = FEMALE_FIT[fit_key]
        layer = tint_layer(_female_asset(name), color, material=material).resize((w, h), Image.Resampling.LANCZOS)
        output.alpha_composite(layer, (x, y))

    add("girl_avatar.png", "body", resolve_skin_tone(skin_tone), material="skin")
    if bottom_style == "pants":
        # Covered anatomy must not leak around the narrower trouser silhouette.
        # Keep the hands outside the hip region and the feet below the ankles.
        alpha = output.getchannel("A")
        draw = ImageDraw.Draw(alpha)
        draw.rectangle((177, 235, 271, 329), fill=0)
        draw.rectangle((0, 330, 447, 509), fill=0)
        output.putalpha(alpha)
    for side in ("left", "right"):
        output.alpha_composite(_female_shoe_layer(side, shoe_style, shoes_color))
    if top_style == "dress":
        add("dress.png", "dress", resolve_color(shirt_color))
        return _fit_output(output, width, height)
    if top_style == "shirt" and bottom_style == "skirt":
        add("girl_shirt.png", "shirt", resolve_color(shirt_color))
    add("skirt.png" if bottom_style == "skirt" else "girl_pants.png", bottom_style, resolve_color(skirt_color), material="denim" if bottom_style == "pants" else "fabric")
    if top_style == "shirt" and bottom_style == "pants":
        add("girl_shirt.png", "shirt", resolve_color(shirt_color))
    elif top_style == "jacket":
        shirt = _fitted_garment("girl cloths/girl_shirt.png", FEMALE_FIT["shirt"], shirt_color)
        output.alpha_composite(_jacket_undershirt(shirt, (191, 91, 257, 247)))
    if top_style in {"hoodie", "jacket"}:
        filename = "girl_hoodie.png" if top_style == "hoodie" else "jacket_girl.png"
        output.alpha_composite(_fitted_garment(f"girl cloths/{filename}", FEMALE_FIT[top_style],
                                               shirt_color if top_style == "hoodie" else outerwear_color))
    return _fit_output(output, width, height)

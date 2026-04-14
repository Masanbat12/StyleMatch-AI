from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

import cv2
import numpy as np
from PIL import Image

from recommendation_engine import SKIN_TONE_OPTIONS


SKIN_TONE_THRESHOLDS = [
    ("very_fair", 210),
    ("fair", 188),
    ("light", 168),
    ("light_medium", 148),
    ("medium", 126),
    ("tan", 108),
    ("deep_tan", 92),
    ("dark", 76),
    ("deep_dark", -1),
]


def _load_image(uploaded_file) -> Image.Image:
    return Image.open(BytesIO(uploaded_file.getvalue())).convert("RGB")


def _rgb_to_hex(rgb: np.ndarray) -> str:
    r, g, b = [int(v) for v in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def _estimate_undertone(mean_rgb: np.ndarray) -> str:
    r, g, b = mean_rgb.astype(float)
    rb_delta = r - b
    rg_delta = r - g

    if abs(rb_delta) <= 8 and abs(rg_delta) <= 12:
        return "neutral"
    if rb_delta > 8:
        return "warm"
    return "cool"


def _estimate_skin_tone_from_brightness(brightness: float) -> str:
    for tone_name, threshold in SKIN_TONE_THRESHOLDS:
        if brightness >= threshold:
            return tone_name
    return "medium"


def _refine_pixels(pixels: np.ndarray) -> np.ndarray:
    if pixels.size == 0:
        return pixels

    brightness = pixels.mean(axis=1)
    low = np.percentile(brightness, 15)
    high = np.percentile(brightness, 85)
    filtered = pixels[(brightness >= low) & (brightness <= high)]

    if filtered.size == 0:
        return pixels
    return filtered


def analyze_skin_from_upload(uploaded_file) -> Dict[str, Any]:
    pil_image = _load_image(uploaded_file)
    rgb = np.array(pil_image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

    h, w, _ = rgb.shape

    x1 = int(w * 0.30)
    x2 = int(w * 0.70)
    y1 = int(h * 0.18)
    y2 = int(h * 0.62)

    focus_rgb = rgb[y1:y2, x1:x2]
    focus_ycrcb = ycrcb[y1:y2, x1:x2]

    lower = np.array([0, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    mask = cv2.inRange(focus_ycrcb, lower, upper)
    skin_pixels = focus_rgb[mask > 0]

    if skin_pixels.size == 0:
        skin_pixels = focus_rgb.reshape(-1, 3)

    skin_pixels = _refine_pixels(skin_pixels)
    mean_rgb = skin_pixels.mean(axis=0)
    brightness = float(mean_rgb.mean())
    undertone = _estimate_undertone(mean_rgb)
    skin_tone = _estimate_skin_tone_from_brightness(brightness)

    swatch = np.zeros((120, 240, 3), dtype=np.uint8)
    swatch[:, :] = mean_rgb.astype(np.uint8)
    swatch_image = Image.fromarray(swatch, mode="RGB")

    return {
        "skin_tone": skin_tone,
        "undertone": undertone,
        "brightness": round(brightness, 2),
        "dominant_skin_rgb": tuple(int(v) for v in mean_rgb),
        "dominant_skin_hex": _rgb_to_hex(mean_rgb),
        "preview_image": pil_image,
        "swatch_image": swatch_image,
        "detected_options": SKIN_TONE_OPTIONS,
        "note": "Improved heuristic estimate using tighter face-centered sampling and highlight/shadow trimming. Best with front-facing photos in natural light.",
    }

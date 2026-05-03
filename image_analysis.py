from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from catalog import SKIN_TONE_OPTIONS
from models import ImageAnalysisResult

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

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MIN_IMAGE_DIMENSION = 80
MIN_SAMPLE_PIXELS = 350
MIN_SAMPLE_COVERAGE = 0.015
HIGHLIGHT_CUTOFF = 245
SHADOW_CUTOFF = 35


class ImageAnalysisError(ValueError):
    pass


def _load_face_detector() -> cv2.CascadeClassifier | None:
    cascade_root = getattr(cv2.data, "haarcascades", "")
    if not cascade_root:
        return None

    detector = cv2.CascadeClassifier(cascade_root + "haarcascade_frontalface_default.xml")
    if detector.empty():
        return None
    return detector


FACE_DETECTOR = _load_face_detector()


@dataclass(slots=True)
class SkinSampleBundle:
    original_pixels: np.ndarray
    balanced_pixels: np.ndarray
    used_fallback: bool
    sample_coverage: float
    used_face_detection: bool


@dataclass(slots=True)
class ImageQualityMetrics:
    mean_brightness: float
    contrast_span: float
    highlight_ratio: float
    shadow_ratio: float
    white_balance_shift: float
    sample_stability: float
    sample_coverage: float
    sample_pixel_count: int
    used_fallback_sampling: bool
    used_face_detection: bool


def _load_image(uploaded_file: Any) -> Image.Image:
    raw_bytes = uploaded_file.getvalue()
    if not raw_bytes:
        raise ImageAnalysisError("The uploaded file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise ImageAnalysisError("Please upload an image smaller than 10 MB.")

    try:
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ImageAnalysisError("The uploaded file is not a supported image.") from exc

    if min(image.size) < MIN_IMAGE_DIMENSION:
        raise ImageAnalysisError("Please upload an image that is at least 80x80 pixels.")
    return image


def _rgb_to_hex(rgb: np.ndarray) -> str:
    r, g, b = [int(v) for v in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def _estimate_skin_tone_from_brightness(brightness: float) -> str:
    for tone_name, threshold in SKIN_TONE_THRESHOLDS:
        if brightness >= threshold:
            return tone_name
    return "medium"


def _luma(pixels: np.ndarray) -> np.ndarray:
    return 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]


def _gray_world_balance(rgb: np.ndarray) -> np.ndarray:
    channel_means = rgb.reshape(-1, 3).mean(axis=0).astype(np.float32)
    gray_mean = float(channel_means.mean())
    safe_means = np.where(channel_means < 1.0, 1.0, channel_means)
    gains = np.clip(gray_mean / safe_means, 0.82, 1.18)
    balanced = np.clip(rgb.astype(np.float32) * gains, 0, 255).astype(np.uint8)
    return balanced


def _focus_region(rgb: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if FACE_DETECTOR is not None:
        min_side = max(60, int(min(rgb.shape[:2]) * 0.18))
        faces = FACE_DETECTOR.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_side, min_side),
        )
        if len(faces):
            x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
            pad_x = int(w * 0.22)
            pad_top = int(h * 0.26)
            pad_bottom = int(h * 0.18)
            x1 = max(0, x - pad_x)
            x2 = min(rgb.shape[1], x + w + pad_x)
            y1 = max(0, y - pad_top)
            y2 = min(rgb.shape[0], y + h + pad_bottom)
            return rgb[y1:y2, x1:x2], True

    height, width, _ = rgb.shape
    x1 = int(width * 0.24)
    x2 = int(width * 0.76)
    y1 = int(height * 0.10)
    y2 = int(height * 0.68)
    return rgb[y1:y2, x1:x2], False


def _build_skin_mask(rgb: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    y = ycrcb[:, :, 0]
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    ycrcb_mask = (cr >= 132) & (cr <= 176) & (cb >= 78) & (cb <= 135)
    hsv_mask = (
        (((h <= 25) | (h >= 165)) & (s >= 18) & (s <= 175) & (v >= 35))
        | ((h >= 5) & (h <= 35) & (s >= 20) & (s <= 190) & (v >= 40))
    )
    luminance_mask = (y >= 32) & (y <= 245)
    mask = (ycrcb_mask & hsv_mask & luminance_mask).astype(np.uint8) * 255

    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def _sample_windows(height: int, width: int) -> list[tuple[int, int, int, int]]:
    return [
        (int(width * 0.36), int(height * 0.13), int(width * 0.64), int(height * 0.29)),
        (int(width * 0.18), int(height * 0.34), int(width * 0.40), int(height * 0.61)),
        (int(width * 0.60), int(height * 0.34), int(width * 0.82), int(height * 0.61)),
    ]


def _filter_stable_pixels(original_pixels: np.ndarray, balanced_pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if original_pixels.size == 0:
        return original_pixels, balanced_pixels

    brightness = _luma(original_pixels)
    saturation = balanced_pixels.max(axis=1) - balanced_pixels.min(axis=1)

    low_brightness = np.percentile(brightness, 12)
    high_brightness = np.percentile(brightness, 88)
    low_saturation = np.percentile(saturation, 10)
    high_saturation = np.percentile(saturation, 92)

    mask = (
        (brightness >= low_brightness)
        & (brightness <= high_brightness)
        & (saturation >= low_saturation)
        & (saturation <= high_saturation)
    )

    filtered_original = original_pixels[mask]
    filtered_balanced = balanced_pixels[mask]
    if filtered_original.size == 0:
        return original_pixels, balanced_pixels
    return filtered_original, filtered_balanced


def _collect_skin_samples(focus_rgb: np.ndarray, used_face_detection: bool) -> SkinSampleBundle:
    balanced_focus = _gray_world_balance(focus_rgb)
    mask = _build_skin_mask(balanced_focus)

    original_samples: list[np.ndarray] = []
    balanced_samples: list[np.ndarray] = []
    windows = _sample_windows(focus_rgb.shape[0], focus_rgb.shape[1])

    for x1, y1, x2, y2 in windows:
        window_mask = mask[y1:y2, x1:x2] > 0
        if not np.any(window_mask):
            continue

        original_window = focus_rgb[y1:y2, x1:x2][window_mask]
        balanced_window = balanced_focus[y1:y2, x1:x2][window_mask]
        original_window, balanced_window = _filter_stable_pixels(original_window, balanced_window)

        if len(original_window) < 45:
            continue
        original_samples.append(original_window)
        balanced_samples.append(balanced_window)

    used_fallback = False
    if original_samples:
        original_pixels = np.concatenate(original_samples, axis=0)
        balanced_pixels = np.concatenate(balanced_samples, axis=0)
    else:
        used_fallback = True
        fallback_mask = mask > 0
        if np.any(fallback_mask):
            original_pixels = focus_rgb[fallback_mask]
            balanced_pixels = balanced_focus[fallback_mask]
        else:
            original_pixels = focus_rgb.reshape(-1, 3)
            balanced_pixels = balanced_focus.reshape(-1, 3)
        original_pixels, balanced_pixels = _filter_stable_pixels(original_pixels, balanced_pixels)

    coverage = len(original_pixels) / float(focus_rgb.shape[0] * focus_rgb.shape[1])
    return SkinSampleBundle(
        original_pixels=original_pixels,
        balanced_pixels=balanced_pixels,
        used_fallback=used_fallback,
        sample_coverage=coverage,
        used_face_detection=used_face_detection,
    )


def _estimate_undertone(mean_balanced_rgb: np.ndarray) -> str:
    rgb = mean_balanced_rgb.astype(np.float32)
    lab = cv2.cvtColor(np.uint8([[np.clip(rgb, 0, 255)]]), cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32)

    rb_delta = float(rgb[0] - rgb[2])
    rg_delta = float(rgb[0] - rgb[1])
    b_star = float(lab[2] - 128.0)
    a_star = float(lab[1] - 128.0)
    warmth_score = (0.68 * rb_delta) + (0.30 * b_star) - (0.12 * a_star)

    if abs(warmth_score) <= 6 and abs(rg_delta) <= 10:
        return "neutral"
    if warmth_score > 0:
        return "warm"
    return "cool"


def _measure_quality(rgb: np.ndarray, sample_bundle: SkinSampleBundle) -> ImageQualityMetrics:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    global_brightness = float(gray.mean())
    contrast_span = float(np.percentile(gray, 95) - np.percentile(gray, 5))
    highlight_ratio = float(np.mean(gray >= HIGHLIGHT_CUTOFF))
    shadow_ratio = float(np.mean(gray <= SHADOW_CUTOFF))

    channel_means = rgb.reshape(-1, 3).mean(axis=0)
    white_balance_shift = float(channel_means.max() - channel_means.min())
    sample_stability = float(sample_bundle.original_pixels.std(axis=0).mean()) if len(sample_bundle.original_pixels) else 100.0

    return ImageQualityMetrics(
        mean_brightness=global_brightness,
        contrast_span=contrast_span,
        highlight_ratio=highlight_ratio,
        shadow_ratio=shadow_ratio,
        white_balance_shift=white_balance_shift,
        sample_stability=sample_stability,
        sample_coverage=sample_bundle.sample_coverage,
        sample_pixel_count=int(len(sample_bundle.original_pixels)),
        used_fallback_sampling=sample_bundle.used_fallback,
        used_face_detection=sample_bundle.used_face_detection,
    )


def _score_confidence(metrics: ImageQualityMetrics) -> tuple[float, str, list[str], dict[str, bool]]:
    confidence = 0.92
    warnings: list[str] = []
    flags = {
        "probable_flash": False,
        "blown_highlights": False,
        "low_light": False,
        "high_contrast": False,
        "strong_color_cast": False,
        "unstable_sampling": False,
        "insufficient_coverage": False,
        "fallback_face_region": False,
    }

    if metrics.highlight_ratio >= 0.08 and metrics.mean_brightness >= 145:
        flags["probable_flash"] = True
        warnings.append("Possible flash or harsh frontal light may be washing out skin color.")
        confidence -= 0.14
    if metrics.highlight_ratio >= 0.12:
        flags["blown_highlights"] = True
        warnings.append("Bright highlights are clipping parts of the image.")
        confidence -= 0.10
    if metrics.mean_brightness <= 72 or metrics.shadow_ratio >= 0.34:
        flags["low_light"] = True
        warnings.append("The image looks dark, so shadow contamination may reduce accuracy.")
        confidence -= 0.13
    if metrics.contrast_span >= 138:
        flags["high_contrast"] = True
        warnings.append("Strong contrast suggests mixed lighting or deep shadows across the face.")
        confidence -= 0.11
    if metrics.white_balance_shift >= 46:
        flags["strong_color_cast"] = True
        warnings.append("A noticeable color cast may be shifting the undertone read.")
        confidence -= 0.08
    if metrics.sample_stability >= 33 or metrics.used_fallback_sampling:
        flags["unstable_sampling"] = True
        warnings.append("Skin sampling was unstable, so the result should be treated as a best estimate.")
        confidence -= 0.12
    if metrics.sample_pixel_count < MIN_SAMPLE_PIXELS or metrics.sample_coverage < MIN_SAMPLE_COVERAGE:
        flags["insufficient_coverage"] = True
        warnings.append("Too little reliable skin area was found for a high-confidence read.")
        confidence -= 0.16
    if not metrics.used_face_detection:
        flags["fallback_face_region"] = True
        warnings.append("A clear face crop was not confirmed, so the center-frame fallback was used.")
        confidence -= 0.06

    confidence = max(0.18, min(confidence, 0.98))
    if confidence >= 0.78:
        label = "high"
    elif confidence >= 0.56:
        label = "medium"
    else:
        label = "low"

    return round(confidence, 2), label, warnings, flags


def _compose_note(confidence_label: str, warnings: list[str]) -> str:
    base = (
        "Best estimate based on central face-region sampling, skin masking, and highlight/shadow rejection."
    )
    if confidence_label == "high":
        return f"{base} Conditions look reasonably stable for this photo."
    if confidence_label == "medium":
        return f"{base} Some lighting noise was detected, so use the result as guided direction."
    if warnings:
        return f"{base} Reliability is limited for this image, so the reading should be treated cautiously."
    return base


def analyze_skin_from_upload(uploaded_file: Any) -> dict[str, Any]:
    pil_image = _load_image(uploaded_file)
    rgb = np.array(pil_image)
    focus_rgb, used_face_detection = _focus_region(rgb)
    sample_bundle = _collect_skin_samples(focus_rgb, used_face_detection)
    metrics = _measure_quality(rgb, sample_bundle)

    original_pixels = sample_bundle.original_pixels
    balanced_pixels = sample_bundle.balanced_pixels
    mean_rgb = original_pixels.mean(axis=0)
    mean_balanced_rgb = balanced_pixels.mean(axis=0)

    brightness = float(_luma(mean_rgb.reshape(1, 3))[0])
    undertone = _estimate_undertone(mean_balanced_rgb)
    skin_tone = _estimate_skin_tone_from_brightness(brightness)
    confidence, confidence_label, warnings, quality_flags = _score_confidence(metrics)

    swatch = np.zeros((120, 240, 3), dtype=np.uint8)
    swatch[:, :] = mean_rgb.astype(np.uint8)
    swatch_image = Image.fromarray(swatch, mode="RGB")

    result = ImageAnalysisResult(
        skin_tone=skin_tone,
        undertone=undertone,
        brightness=round(brightness, 2),
        dominant_skin_rgb=tuple(int(v) for v in mean_rgb),
        dominant_skin_hex=_rgb_to_hex(mean_rgb),
        preview_image=pil_image,
        swatch_image=swatch_image,
        detected_options=SKIN_TONE_OPTIONS,
        confidence=confidence,
        confidence_label=confidence_label,
        warnings=warnings,
        quality_flags=quality_flags,
        sample_pixel_count=metrics.sample_pixel_count,
        note=_compose_note(confidence_label, warnings),
    )
    return result.model_dump()

from __future__ import annotations

from dataclasses import asdict, dataclass

from catalog import ALL_COLORS, OCCASION_OPTIONS, SKIN_TONE_OPTIONS, STYLE_OPTIONS, UNDERTONE_OPTIONS


def _ensure_supported(value: str, allowed: list[str], label: str) -> str:
    if value not in allowed:
        raise ValueError(f"Unsupported {label}: {value}")
    return value


@dataclass(slots=True)
class UserProfile:
    skin_tone: str
    undertone: str
    style: str
    occasion: str

    def __post_init__(self) -> None:
        self.skin_tone = _ensure_supported(self.skin_tone, SKIN_TONE_OPTIONS, "skin tone")
        self.undertone = _ensure_supported(self.undertone, UNDERTONE_OPTIONS, "undertone")
        self.style = _ensure_supported(self.style, STYLE_OPTIONS, "style")
        self.occasion = _ensure_supported(self.occasion, OCCASION_OPTIONS, "occasion")


@dataclass(slots=True)
class Outfit:
    shirt_color: str
    pants_color: str
    shoes_color: str
    score: int = 0

    def __post_init__(self) -> None:
        self.shirt_color = _ensure_supported(self.shirt_color, ALL_COLORS, "color")
        self.pants_color = _ensure_supported(self.pants_color, ALL_COLORS, "color")
        self.shoes_color = _ensure_supported(self.shoes_color, ALL_COLORS, "color")
        if not 0 <= self.score <= 100:
            raise ValueError(f"Unsupported score: {self.score}")


@dataclass(slots=True)
class ImageAnalysisResult:
    skin_tone: str
    undertone: str
    brightness: float
    dominant_skin_rgb: tuple[int, int, int]
    dominant_skin_hex: str
    preview_image: object
    swatch_image: object
    detected_options: list[str]
    confidence: float
    confidence_label: str
    warnings: list[str]
    quality_flags: dict[str, bool]
    sample_pixel_count: int
    note: str

    def __post_init__(self) -> None:
        self.skin_tone = _ensure_supported(self.skin_tone, SKIN_TONE_OPTIONS, "skin tone")
        self.undertone = _ensure_supported(self.undertone, UNDERTONE_OPTIONS, "undertone")
        if self.brightness < 0:
            raise ValueError("Brightness must be non-negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1.")
        if self.confidence_label not in {"high", "medium", "low"}:
            raise ValueError(f"Unsupported confidence label: {self.confidence_label}")
        if self.sample_pixel_count < 0:
            raise ValueError("Sample pixel count must be non-negative.")

    def model_dump(self) -> dict[str, object]:
        return asdict(self)

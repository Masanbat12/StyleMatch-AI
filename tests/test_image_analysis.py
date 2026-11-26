from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from image_analysis import analyze_skin_from_upload


class UploadStub:
    def __init__(self, image: Image.Image) -> None:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        self._data = buffer.getvalue()

    def getvalue(self) -> bytes:
        return self._data


def _make_portrait(base_rgb: tuple[int, int, int], background_rgb: tuple[int, int, int]) -> Image.Image:
    image = np.zeros((320, 240, 3), dtype=np.uint8)
    image[:, :] = background_rgb
    image[48:250, 72:168] = base_rgb
    image[88:130, 88:152] = np.clip(np.array(base_rgb) + 10, 0, 255)
    image[140:210, 92:148] = np.clip(np.array(base_rgb) - 8, 0, 255)
    return Image.fromarray(image, mode="RGB")


def test_analyze_skin_returns_confidence_and_quality_fields():
    portrait = _make_portrait((198, 142, 104), (40, 42, 44))
    result = analyze_skin_from_upload(UploadStub(portrait))

    assert 0 <= result["confidence"] <= 1
    assert result["confidence_label"] in {"high", "medium", "low"}
    assert isinstance(result["warnings"], list)
    assert isinstance(result["quality_flags"], dict)
    assert result["sample_pixel_count"] > 0


def test_analyze_skin_flags_low_light_images():
    portrait = _make_portrait((78, 58, 44), (8, 8, 10))
    result = analyze_skin_from_upload(UploadStub(portrait))

    assert result["quality_flags"]["low_light"] is True
    assert result["confidence"] < 0.8


def test_invalid_uploads_have_actionable_errors():
    import pytest
    from image_analysis import _load_image, ImageAnalysisError
    for raw in (b"", b"not an image", b"\x89PNG\r\n\x1a\n" + b"broken" * 30):
        upload = BytesIO(raw)
        with pytest.raises(ImageAnalysisError):
            _load_image(upload)


def test_large_images_are_resized_for_analysis():
    from image_analysis import _load_image, MAX_ANALYSIS_DIMENSION
    image = _load_image(UploadStub(Image.new("RGB", (2400, 1800))))
    assert image.size == (MAX_ANALYSIS_DIMENSION, 1200)


def test_oversized_pixel_dimensions_are_rejected(monkeypatch):
    import pytest
    import image_analysis
    monkeypatch.setattr(image_analysis, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(image_analysis.ImageAnalysisError, match="million pixels"):
        image_analysis._load_image(UploadStub(Image.new("RGB", (80, 80))))


def test_exif_orientation_is_applied():
    from image_analysis import _load_image
    image = Image.new("RGB", (120, 80))
    exif = image.getexif()
    exif[274] = 6
    upload = BytesIO()
    image.save(upload, format="JPEG", exif=exif)
    assert _load_image(upload).size == (80, 120)

"""Light-aware recoloring of baked PNG assets; no 3D geometry or relighting.

Inspired by the supplied Blender material setup. Roughness and specular here
control a restrained image-space highlight, not a physical BSDF simulation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Material:
    roughness: float
    specular: float


MATERIALS = {
    "fabric": Material(0.85, 0.10),
    "denim": Material(0.70, 0.20),
    "jacket": Material(0.80, 0.15),
    "shoes": Material(0.55, 0.25),
}


def _linear(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def recolor_material(image: Image.Image, color: tuple[int, int, int], material: str = "fabric") -> Image.Image:
    settings = MATERIALS[material]
    rgba = np.array(image.convert("RGBA"))
    visible = rgba[:, :, 3] >= 128
    if not visible.any():
        return Image.fromarray(rgba)
    rgb = _linear(rgba[:, :, :3].astype(np.float32) / 255.0)
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    # Transparent padding must never change the garment's exposure.
    reference = max(float(np.percentile(luminance[visible], 95)), 0.05)
    shading = np.clip(luminance / reference, 0.0, 1.15)
    base = _linear(np.asarray(color, dtype=np.float32) / 255.0)
    diffuse = shading[:, :, None] * base
    highlight = np.clip((shading - 0.60) / 0.55, 0, 1) ** 3
    strength = (1 - settings.roughness) * settings.specular * 0.06
    linear = np.clip(diffuse + highlight[:, :, None] * strength, 0, 1)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    rgba[:, :, :3] = np.rint(np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    # Alpha is copied exactly, including antialiased edges.
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return Image.fromarray(rgba)

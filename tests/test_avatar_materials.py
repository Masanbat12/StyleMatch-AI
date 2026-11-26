import numpy as np
from PIL import Image

from avatar_materials import recolor_material


def _swatch():
    rgba = np.zeros((12, 60, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.linspace(35, 240, 60).astype(np.uint8)[None, :, None]
    rgba[:, :, 3] = 255
    rgba[0, :, 3] = np.linspace(0, 255, 60).astype(np.uint8)
    return Image.fromarray(rgba)


def test_recolor_keeps_alpha_and_folds_in_dark_fabric():
    source = _swatch()
    result = np.array(recolor_material(source, (26, 26, 26)))
    assert np.array_equal(result[:, :, 3], np.array(source)[:, :, 3])
    assert np.ptp(result[5, :, 0]) > 15
    assert np.all(np.diff(result[5, :, 0].astype(int)) >= 0)


def test_transparent_padding_does_not_change_exposure():
    source = _swatch()
    padded = Image.new("RGBA", (200, 200))
    padded.alpha_composite(source, (30, 40))
    original = recolor_material(source, (128, 0, 32))
    result = recolor_material(padded, (128, 0, 32)).crop((30, 40, 90, 52))
    assert original.tobytes() == result.tobytes()


def test_material_highlight_changes_without_touching_alpha():
    source = _swatch()
    fabric = np.array(recolor_material(source, (26, 26, 26), "fabric"))
    shoes = np.array(recolor_material(source, (26, 26, 26), "shoes"))
    assert np.array_equal(fabric[:, :, 3], shoes[:, :, 3])
    assert shoes[5, -1, 0] > fabric[5, -1, 0]

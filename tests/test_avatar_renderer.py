from avatar_renderer import render_avatar, resolve_skin_tone
from catalog import SKIN_TONE_OPTIONS


def test_all_skin_tones_have_avatar_mapping():
    for tone in SKIN_TONE_OPTIONS:
        assert resolve_skin_tone(tone) != resolve_skin_tone("__missing__")


def test_render_avatar_returns_expected_size():
    avatar = render_avatar(
        skin_tone="light_medium",
        shirt_color="navy",
        pants_color="black",
        shoes_color="white",
        width=240,
        height=360,
    )

    assert avatar.size == (240, 360)


def test_female_wardrobe_and_footwear_are_distinct():
    kwargs = dict(skin_tone="medium", shirt_color="navy", pants_color="burgundy", shoes_color="white")
    male = render_avatar(**kwargs)
    female = render_avatar(**kwargs, avatar_model="female")
    heels = render_avatar(**kwargs, avatar_model="female", shoe_style="heels")
    assert female.size == male.size == heels.size
    assert female.tobytes() != male.tobytes()
    assert female.tobytes() != heels.tobytes()


def test_female_skin_and_garment_colors_change_independently():
    from PIL import ImageChops
    kwargs = dict(skin_tone="fair", shirt_color="white", pants_color="black", shoes_color="white", avatar_model="female", width=448, height=557)
    base = render_avatar(**kwargs)
    shirt = render_avatar(**{**kwargs, "shirt_color": "navy"})
    skin = render_avatar(**{**kwargs, "skin_tone": "dark"})
    assert base.getpixel((224, 45)) == shirt.getpixel((224, 45))
    assert base.getpixel((224, 45)) != skin.getpixel((224, 45))
    assert ImageChops.difference(base.convert("RGB"), shirt.convert("RGB")).getbbox()
    assert base.getpixel((224, 300)) == shirt.getpixel((224, 300))


def test_female_assets_have_clean_transparent_padding():
    image = render_avatar("fair", "white", "black", "white", avatar_model="female", width=448, height=557)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((447, 556))[3] == 0
    # The waist seam and shoulders remain covered by clothing.
    for point in ((224, 240), (183, 112), (265, 112)):
        assert image.getpixel(point)[3] > 240


def test_female_skirt_keeps_asset_proportions_and_covers_shirt_at_waist():
    from avatar_renderer import FEMALE_FIT, _female_asset
    asset = _female_asset("skirt.png")
    x, y, width, height = FEMALE_FIT["skirt"]
    assert abs(width / height - asset.width / asset.height) < 0.01
    dark = render_avatar("fair", "white", "black", "white", avatar_model="female", width=448, height=557)
    light = render_avatar("fair", "white", "white", "white", avatar_model="female", width=448, height=557)
    # Waistband must remain visible over the shirt, rather than being hidden under its hem.
    waist = (224, y + 7)
    assert max(dark.getpixel(waist)[:3]) < 40
    assert light.getpixel(waist) != dark.getpixel(waist)


def test_female_shoes_cover_toes_on_both_feet():
    import numpy as np
    from PIL import Image
    from avatar_renderer import FEMALE_FIT, _female_asset, _female_shoe_layer
    body = Image.new("RGBA", (448, 557))
    x, y, width, height = FEMALE_FIT["body"]
    body.alpha_composite(_female_asset("girl_avatar.png").resize((width, height)), (x, y))
    feet = np.asarray(body)[510:530, :, 3] > 200
    assert feet.sum() > 500
    for style in ("sneakers", "heels"):
        shoes = Image.alpha_composite(_female_shoe_layer("left", style, "white"),
                                     _female_shoe_layer("right", style, "white"))
        covered = np.asarray(shoes)[510:530, :, 3] >= 180
        assert np.all(covered[feet]), f"Bare toes protrude from {style}"


def test_male_shoes_connect_to_both_pant_hems():
    # An opaque ankle-to-shoe seam must survive different preview sizes.
    for width, height in ((448, 557), (224, 279)):
        image = render_avatar("medium", "white", "green", "white", width=width, height=height)
        # Fit coordinates into the letterboxed preview just as the renderer does.
        scale = min(width / 448, height / 557)
        offset_x = (width - round(448 * scale)) // 2
        offset_y = (height - round(557 * scale)) // 2
        for ankle_x in (185, 260):
            for y in range(480, 504):
                point = (round(ankle_x * scale) + offset_x, round(y * scale) + offset_y)
                assert image.getpixel(point)[3] >= 240


def test_new_wardrobe_combinations_render_without_covering_the_face():
    import pytest
    from PIL import ImageChops
    kwargs = dict(skin_tone="fair", shirt_color="white", pants_color="navy", shoes_color="white", width=448, height=557)
    for model in ("male", "female"):
        reference = render_avatar(**kwargs, avatar_model=model)
        for bottom in (("pants",) if model == "male" else ("skirt", "pants")):
            for top in ("shirt", "hoodie", "jacket"):
                rendered = render_avatar(**kwargs, avatar_model=model, top_style=top, bottom_style=bottom)
                assert rendered.size == (448, 557)
                assert rendered.getpixel((224, 45)) == reference.getpixel((224, 45))
                if top != "shirt":
                    assert ImageChops.difference(rendered.convert("RGB"), reference.convert("RGB")).getbbox()
    with pytest.raises(ValueError):
        render_avatar(**kwargs, avatar_model="male", bottom_style="skirt")


def test_jacket_color_does_not_change_skin_or_bottom():
    kwargs = dict(skin_tone="medium", shirt_color="white", pants_color="navy", shoes_color="white", top_style="jacket", width=448, height=557)
    for model in ("male", "female"):
        first = render_avatar(**kwargs, avatar_model=model, outerwear_color="white")
        second = render_avatar(**kwargs, avatar_model=model, outerwear_color="black")
        assert first.getpixel((224, 45)) == second.getpixel((224, 45))
        assert first.getpixel((205, 400)) == second.getpixel((205, 400))
        assert first.getpixel((202, 160)) != second.getpixel((202, 160))


def test_shirt_color_is_visible_inside_both_jackets():
    for model in ("male", "female"):
        kwargs = dict(skin_tone="medium", pants_color="black", shoes_color="white",
                      width=448, height=557, avatar_model=model, top_style="jacket",
                      outerwear_color="charcoal")
        white = render_avatar(**kwargs, shirt_color="white")
        burgundy = render_avatar(**kwargs, shirt_color="burgundy")
        # The chest inside the open jacket shows the selected shirt, while
        # sleeves, lapels and the face retain their own colors.
        assert white.getpixel((224, 160)) != burgundy.getpixel((224, 160))
        assert min(white.getpixel((224, 160))[:3]) > 100
        for point in ((202, 160), (165, 190), (224, 45)):
            assert white.getpixel(point) == burgundy.getpixel(point)


def test_covered_female_legs_do_not_leak_skin_around_pants():
    kwargs = dict(shirt_color="white", pants_color="black", shoes_color="white",
                  avatar_model="female", bottom_style="pants", width=448, height=557)
    fair = render_avatar(**kwargs, skin_tone="fair")
    dark = render_avatar(**kwargs, skin_tone="dark")
    assert fair.crop((177, 335, 272, 510)).tobytes() == dark.crop((177, 335, 272, 510)).tobytes()


def test_hoodie_cuffs_leave_hands_visible_and_male_hip_has_no_stray_skin():
    import numpy as np
    for model in ("male", "female"):
        kwargs = dict(shirt_color="white", pants_color="black", shoes_color="white",
                      avatar_model=model, top_style="hoodie", width=448, height=557)
        fair = render_avatar(**kwargs, skin_tone="fair")
        dark = render_avatar(**kwargs, skin_tone="dark")
        for box in ((135, 287, 178, 325), (270, 287, 315, 325)):
            difference = np.any(np.asarray(fair.crop(box)) != np.asarray(dark.crop(box)), axis=2)
            assert difference.sum() > 20, f"{model} hoodie hides the hand"
    assert render_avatar("medium", "white", "black", "white", width=448, height=557).getpixel((276, 320))[3] == 0


def test_dress_is_one_piece_and_ignores_hidden_bottom_color():
    kwargs = dict(skin_tone="medium", shirt_color="burgundy", shoes_color="white", avatar_model="female", top_style="dress")
    dress = render_avatar(**kwargs, pants_color="black")
    assert dress.tobytes() == render_avatar(**kwargs, pants_color="white").tobytes()
    assert dress.tobytes() != render_avatar(**{**kwargs, "shirt_color": "navy"}, pants_color="black").tobytes()

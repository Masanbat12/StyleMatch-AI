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

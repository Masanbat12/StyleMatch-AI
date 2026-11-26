"""Render the 30-second StyleMatch AI promo (1920x1080, 30 fps) with Pillow + OpenCV.

Run from the project root:
    .venv-run/Scripts/python.exe promo/render_promo.py            # full MP4
    .venv-run/Scripts/python.exe promo/render_promo.py --stills   # key frames only (PNG)

All outfit colours, scores and reasons come from the real engine and avatar renderer.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avatar_renderer import render_avatar  # noqa: E402
from catalog import COLOR_MAP, SKIN_TONE_MAP, SKIN_TONE_OPTIONS  # noqa: E402
import recommendation_engine as engine  # noqa: E402

W, H, FPS, TOTAL = 1920, 1080, 30, 900
OUT_DIR = Path(__file__).resolve().parent
FONTS = Path("C:/Windows/Fonts")

BONE = (247, 245, 242)
PAPER = (255, 255, 255)
INK = (31, 26, 23)
MUTED = (107, 97, 89)
LINE = (230, 224, 216)
BRASS = (156, 122, 60)
BRASS_SOFT = (239, 229, 210)
ESPRESSO = (23, 18, 15)
WARM_LIGHT = (205, 191, 168)
CREDIT = (140, 123, 102)

PROFILE = dict(skin_tone="medium", undertone="warm", style="elegant", occasion="work")
BUILDER_OUTFITS = [("icy blue", "gray", "white"), ("rust", "beige", "brown"), ("camel", "navy", "brown")]


# ---------------------------------------------------------------- helpers
def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def prog(f, start, dur, ease=ease_out):
    return ease(clamp((f - start) / dur))


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


DISPLAY, DISPLAY_I, BODY, BODY_L, BODY_SB = "georgia.ttf", "georgiai.ttf", "segoeui.ttf", "segoeuil.ttf", "seguisb.ttf"


@lru_cache(maxsize=None)
def text_sprite(text, face, size, color):
    f = font(face, size)
    left, top, right, bottom = f.getbbox(text)
    ascent, descent = f.getmetrics()
    img = Image.new("RGBA", (right + 4, ascent + descent + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=f, fill=color + (255,))
    return img


def with_alpha(sprite, alpha):
    if alpha >= 0.999:
        return sprite
    out = sprite.copy()
    out.putalpha(sprite.getchannel("A").point(lambda v: int(v * alpha)))
    return out


def paste(canvas, sprite, x, y, alpha=1.0, anchor="lt"):
    if alpha <= 0.001:
        return
    w, h = sprite.size
    if anchor[0] == "m":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    canvas.alpha_composite(with_alpha(sprite, alpha), (int(round(x)), int(round(y))))


def text(canvas, x, y, s, face, size, color, alpha=1.0, anchor="lt"):
    paste(canvas, text_sprite(s, face, size, color), x, y, alpha, anchor)


def wrap(s, face, size, width):
    words, lines, line = s.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if font(face, size).getlength(trial) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def paragraph(canvas, x, y, s, face, size, color, width, alpha=1.0, leading=1.45):
    for i, line in enumerate(wrap(s, face, size, width)):
        text(canvas, x, y + i * size * leading, line, face, size, color, alpha)


@lru_cache(maxsize=None)
def rounded(w, h, r, fill, outline=None, stroke=0):
    s = 3
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), radius=r * s, fill=None if fill is None else fill + (255,),
        outline=None if outline is None else outline + (255,), width=stroke * s)
    return img.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=None)
def disc(d, fill, ring=None, ring_w=0):
    s = 4
    img = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if fill is not None:
        draw.ellipse((0, 0, d * s - 1, d * s - 1), fill=fill + (255,))
    if ring is not None:
        draw.ellipse((0, 0, d * s - 1, d * s - 1), outline=ring + (255,), width=ring_w * s)
    return img.resize((d, d), Image.LANCZOS)


def scaled(sprite, k):
    if abs(k - 1) < 0.01:
        return sprite
    w, h = max(1, int(sprite.width * k)), max(1, int(sprite.height * k))
    return sprite.resize((w, h), Image.BILINEAR)


def bg(color):
    return Image.new("RGBA", (W, H), color + (255,))


# ---------------------------------------------------------------- assets
def crop_alpha(img):
    return img.crop(img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())


LOGO = crop_alpha(Image.open(ROOT / "assets" / "logo.png").convert("RGBA"))


@lru_cache(maxsize=None)
def logo(height):
    return LOGO.resize((int(LOGO.width * height / LOGO.height), height), Image.LANCZOS)


@lru_cache(maxsize=None)
def avatar(outfit, w, h):
    shirt, pants, shoes = outfit
    return render_avatar(PROFILE["skin_tone"], shirt, pants, shoes, width=w, height=h).convert("RGBA")


def report(outfit):
    return engine.score_report(PROFILE["skin_tone"], PROFILE["undertone"], PROFILE["style"],
                               PROFILE["occasion"], *outfit)


SEASON = report(BUILDER_OUTFITS[0])["season"]
PALETTE = engine.get_recommended_colors(PROFILE["undertone"], PROFILE["style"], PROFILE["occasion"])[:8]
LOOKS = engine.generate_outfit_suggestions(**PROFILE, limit=5)
BUILDER = []
for outfit in BUILDER_OUTFITS:
    rep = report(outfit)
    lines = [(True, rep["strengths"][0])] + ([(False, rep["risks"][0])] if rep["risks"] else [(True, rep["strengths"][1])])
    BUILDER.append(dict(outfit=outfit, score=rep["score"], label=rep["label"], lines=lines))


def brand_mark(canvas):
    paste(canvas, logo(40), 140, 64)
    text(canvas, 140 + logo(40).width + 16, 62, "StyleMatch", DISPLAY, 30, INK)


# ---------------------------------------------------------------- scenes
def scene_intro(f):
    c = bg(ESPRESSO)
    a = prog(f, 0, 30)
    paste(c, logo(150), W / 2, 330 + 24 * (1 - a), a, "mm")
    word, size = "StyleMatch", 128
    total = font(DISPLAY, size).getlength(word)
    x0 = W / 2 - total / 2
    for i, ch in enumerate(word):
        t = prog(f, 18 + i * 3, 22)
        x = x0 + font(DISPLAY, size).getlength(word[:i])
        text(c, x, 470 + 30 * (1 - t), ch, DISPLAY, size, BONE, t)
    rule = prog(f, 50, 30, ease_in_out)
    if rule > 0:
        ImageDraw.Draw(c).line((W / 2 - 130 * rule, 650, W / 2 + 130 * rule, 650), fill=BRASS + (255,), width=2)
    text(c, W / 2, 690, "Colour that suits you, before you get dressed.", BODY_L, 40, WARM_LIGHT,
         prog(f, 62, 28), "mt")
    return c


def scene_complexion(f):
    c = bg(BONE)
    brand_mark(c)
    text(c, 140, 190, "Start with your complexion.", DISPLAY, 76, INK, prog(f, 4, 22))
    paragraph(c, 140, 300, "Upload a photo or pick your tone. StyleMatch reads your undertone "
              "and finds your colour season.", BODY_L, 34, MUTED, 980, prog(f, 10, 22))
    d, gap, y = 112, 30, 470
    selected = SKIN_TONE_OPTIONS.index(PROFILE["skin_tone"])
    for i, tone in enumerate(SKIN_TONE_OPTIONS):
        t = prog(f, 16 + i * 4, 20)
        if t <= 0:
            continue
        cx = 140 + d / 2 + i * (d + gap)
        paste(c, scaled(disc(d, hex_rgb(SKIN_TONE_MAP[tone]), LINE, 2), 0.6 + 0.4 * t), cx, y + d / 2, t, "mm")
    ring = prog(f, 62, 18)
    cx = 140 + d / 2 + selected * (d + gap)
    paste(c, scaled(disc(d + 26, None, BRASS, 4), 1.25 - 0.25 * ring), cx, y + d / 2, ring, "mm")
    text(c, cx, y + d + 26, "Medium", BODY_SB, 26, INK, ring, "mt")

    chips = ["Cool", "Neutral", "Warm"]
    picked = prog(f, 96, 14)
    for i, label in enumerate(chips):
        t = prog(f, 74 + i * 5, 18)
        x = 140 + i * 236
        paste(c, rounded(212, 72, 36, PAPER, LINE, 2), x, 720 + 16 * (1 - t), t)
        if label == "Warm":
            paste(c, rounded(212, 72, 36, ESPRESSO), x, 720, picked)
        color = BONE if (label == "Warm" and picked > 0.5) else INK
        text(c, x + 106, 756 + 16 * (1 - t), label, BODY, 30, color, t, "mm")
    text(c, 140, 820, "Undertone", BODY, 24, MUTED, prog(f, 74, 18))

    s = prog(f, 112, 24)
    paste(c, rounded(560, 250, 18, PAPER, LINE, 2), 868, 690 + 30 * (1 - s), s)
    text(c, 918, 726 + 30 * (1 - s), "Your colour season", BODY, 26, MUTED, s)
    text(c, 918, 768 + 30 * (1 - s), SEASON, DISPLAY_I, 76, BRASS, s)
    text(c, 918, 872 + 30 * (1 - s), "Medium skin, warm undertone", BODY, 26, INK, s)
    return c


def scene_palette(f):
    c = bg(BONE)
    brand_mark(c)
    text(c, 140, 190, "A palette made for you.", DISPLAY, 76, INK, prog(f, 4, 22))
    text(c, 140, 300, f"{SEASON} colours that light up your face, ranked by the style engine.",
         BODY_L, 34, MUTED, prog(f, 10, 22))
    sw, gap, top, full = 180, 26, 400, 400
    x0 = (W - (len(PALETTE) * sw + (len(PALETTE) - 1) * gap)) / 2
    for i, name in enumerate(PALETTE):
        t = prog(f, 22 + i * 6, 26, ease_in_out)
        if t <= 0:
            continue
        h = max(2, int(full * t))
        x = x0 + i * (sw + gap)
        paste(c, rounded(sw, h, 8, hex_rgb(COLOR_MAP[name]), LINE, 2), x, top)
        text(c, x + sw / 2, top + full + 26, name.title(), BODY, 26, INK, prog(f, 36 + i * 6, 18), "mt")
    return c


def scene_builder(f):
    c = bg(BONE)
    brand_mark(c)
    seg_starts = [0, 78, 146]
    idx = 2 if f >= seg_starts[2] else 1 if f >= seg_starts[1] else 0

    # avatar card + crossfading avatars
    card_in = prog(f, 0, 22)
    paste(c, rounded(600, 820, 22, PAPER, LINE, 2), 140, 170 + 30 * (1 - card_in), card_in)
    for i, start in enumerate(seg_starts):
        end = seg_starts[i + 1] if i + 1 < len(seg_starts) else 10_000
        a = prog(f, start, 12) * (1 - prog(f, end, 12))
        if i == 0:
            a *= card_in
        if a > 0:
            paste(c, avatar(BUILDER[i]["outfit"], 520, 760), 440, 580 + 30 * (1 - card_in), a, "mm")

    x = 860
    text(c, x, 190, "Every outfit gets an honest score.", DISPLAY, 62, INK, prog(f, 4, 22))

    data = BUILDER[idx]
    previous = BUILDER[idx - 1]["score"] if idx else 0
    count = prog(f, seg_starts[idx] + (14 if idx == 0 else 0), 30)
    shown = round(previous + (data["score"] - previous) * count)
    appear = prog(f, 12, 18)

    # outfit chips
    for j, (slot, color) in enumerate(zip(("Top", "Bottom", "Shoes"), data["outfit"])):
        cx = x + j * 290
        a = appear * prog(f, seg_starts[idx], 10) if idx else appear
        paste(c, disc(36, hex_rgb(COLOR_MAP[color]), LINE, 2), cx, 320, a)
        text(c, cx + 50, 318, slot, BODY, 22, MUTED, a)
        text(c, cx + 50, 342, color.title(), BODY_SB, 26, INK, a)

    text(c, x - 6, 410, f"{shown}", DISPLAY, 230, BRASS, appear)
    num_w = font(DISPLAY, 230).getlength(f"{shown}")
    text(c, x + num_w + 14, 560, "/ 100", BODY_L, 40, MUTED, appear)
    text(c, x, 676, data["label"], DISPLAY_I, 46, INK, appear * prog(f, seg_starts[idx] + 16, 14))

    rail_w = 880
    draw = ImageDraw.Draw(c)
    if appear > 0:
        draw.rounded_rectangle((x, 740, x + rail_w, 746), radius=3, fill=LINE + (int(255 * appear),))
        fill = rail_w * shown / 100
        if fill > 4:
            draw.rounded_rectangle((x, 740, x + fill, 746), radius=3, fill=BRASS + (int(255 * appear),))

    for k, (good, line) in enumerate(data["lines"]):
        a = prog(f, seg_starts[idx] + 24 + k * 8, 16)
        y = 800 + k * 62
        paste(c, disc(16, BRASS if good else None, None if good else MUTED, 2), x, y + 12, a)
        text(c, x + 34, y, line, BODY, 30, INK if good else MUTED, a)
    return c


def scene_looks(f):
    c = bg(BONE)
    brand_mark(c)
    text(c, 140, 170, "Five looks, ranked for your day.", DISPLAY, 76, INK, prog(f, 4, 22))
    text(c, 140, 278, "Elegant style for work, scored against your season.", BODY_L, 34, MUTED, prog(f, 10, 22))
    cw, ch, gap = 300, 600, 30
    x0 = (W - (5 * cw + 4 * gap)) / 2
    for i, look in enumerate(LOOKS):
        t = prog(f, 16 + i * 7, 26)
        if t <= 0:
            continue
        x = x0 + i * (cw + gap) + 90 * (1 - t)
        y = 370
        paste(c, rounded(cw, ch, 18, PAPER, BRASS if i == 0 else LINE, 3 if i == 0 else 2), x, y, t)
        outfit = (look["shirt_color"], look["pants_color"], look["shoes_color"])
        paste(c, avatar(outfit, 250, 360), x + cw / 2, y + 30, t, "mt")
        for j, color in enumerate(outfit):
            paste(c, disc(30, hex_rgb(COLOR_MAP[color]), LINE, 2), x + 26 + j * 40, y + 420, t)
        text(c, x + cw - 26, y + 405, str(look["score"]), DISPLAY, 56, BRASS, t, "rt")
        text(c, x + 26, y + 486, look["harmony"].replace("-", " ").capitalize(), BODY, 22, MUTED, t)
        text(c, x + 26, y + 520, " / ".join(o.title() for o in outfit), BODY, 21, INK, t)
        if i == 0:
            text(c, x + 26, y + 556, "Top pick", BODY_SB, 21, BRASS, t)
    return c


def scene_end(f):
    c = bg(ESPRESSO)
    a = prog(f, 4, 26)
    paste(c, logo(130), W / 2, 360 + 20 * (1 - a), a, "mm")
    text(c, W / 2, 450 + 20 * (1 - a), "StyleMatch AI", DISPLAY, 104, BONE, a, "mt")
    text(c, W / 2, 610, "Dress in colours that work with you.", BODY_L, 40, WARM_LIGHT, prog(f, 22, 24), "mt")
    text(c, W / 2, 1000, "Created by Masanbat Mulu", BODY, 24, CREDIT, prog(f, 40, 24), "mb")
    return c


# (scene, start, end) in global frames; 12-frame crossfades on the overlaps.
SCENES = [
    (scene_intro, 0, 132),
    (scene_complexion, 120, 282),
    (scene_palette, 270, 432),
    (scene_builder, 420, 642),
    (scene_looks, 630, 792),
    (scene_end, 780, 900),
]


def frame(g):
    active = [(fn, s, e) for fn, s, e in SCENES if s <= g < e]
    if len(active) == 1:
        fn, s, _ = active[0]
        img = fn(g - s)
    else:
        # Dip through the incoming scene's background so headings never ghost over each other.
        (fa, sa, ea), (fb, sb, _) = active[:2]
        t = clamp((g - sb) / (ea - sb))
        incoming = fb(g - sb)
        plain = bg(incoming.getpixel((W - 1, H - 1))[:3])
        if t < 0.5:
            img = Image.blend(fa(g - sa), plain, ease_in_out(t * 2))
        else:
            img = Image.blend(plain, incoming, ease_in_out(t * 2 - 1))
    return img.convert("RGB")


def main():
    if "--stills" in sys.argv:
        for g in (60, 115, 200, 390, 500, 600, 760, 870):
            frame(g).save(OUT_DIR / f"still_{g:03d}.png")
        print("stills written")
        return
    out = OUT_DIR / "stylematch_promo.mp4"
    music = OUT_DIR / "stylematch_music.wav"
    try:
        import subprocess
        import imageio_ffmpeg
    except ImportError:
        imageio_ffmpeg = None
    if imageio_ffmpeg is not None and music.exists():
        # H.264 + AAC with the soundtrack: plays on phones, WhatsApp, Instagram and browsers.
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(music), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
               str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for g in range(TOTAL):
            proc.stdin.write(frame(g).tobytes())
            if g % 150 == 0:
                print(f"frame {g}/{TOTAL}", flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit("ffmpeg failed")
        print(f"wrote {out.name} (H.264 + AAC)")
        return
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not writer.isOpened():
        raise SystemExit("could not open video writer")
    for g in range(TOTAL):
        writer.write(cv2.cvtColor(np.asarray(frame(g)), cv2.COLOR_RGB2BGR))
        if g % 150 == 0:
            print(f"frame {g}/{TOTAL}", flush=True)
    writer.release()
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()

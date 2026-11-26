from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import streamlit as st


SKIN_TONE_LABELS = {
    "fair": "Fair",
    "light": "Light",
    "light_medium": "Light Medium",
    "medium": "Medium",
    "tan": "Tan",
    "deep_tan": "Deep Tan",
    "dark": "Dark",
    "very_fair": "Fair",
    "deep_dark": "Dark",
}

SKIN_TONE_SWATCHES = {
    "fair": "#F3D7C6",
    "light": "#EAC09B",
    "light_medium": "#D9A074",
    "medium": "#B97C56",
    "tan": "#9A623F",
    "deep_tan": "#6F432C",
    "dark": "#4B2E22",
    "very_fair": "#F3D7C6",
    "deep_dark": "#4B2E22",
}

UNDERTONE_META = {
    "warm": ("☀", "Warm"),
    "neutral": ("◐", "Neutral"),
    "cool": ("❄", "Cool"),
}

STYLE_META = {
    "casual": ("👕", "Casual"),
    "elegant": ("✦", "Elegant"),
    "street": ("🧢", "Street"),
    "minimal": ("▣", "Minimal"),
}

OCCASION_META = {
    "daily": ("☀", "Daily"),
    "date": ("❤", "Date"),
    "work": ("💼", "Work"),
    "evening": ("☾", "Evening"),
}


def _image_to_data_uri(path: str | Path) -> str:
    image_path = Path(path)
    if not image_path.exists():
        return ""
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    suffix = image_path.suffix.lower().lstrip(".") or "png"
    return f"data:image/{suffix};base64,{encoded}"


def humanize_value(value: str) -> str:
    if value in SKIN_TONE_LABELS:
        return SKIN_TONE_LABELS[value]
    return value.replace("_", " ").title()


def choice_label(option: str, meta: dict[str, tuple[str, str]]) -> str:
    icon, label = meta[option]
    return f"{icon} {label}"


_card_counter = {"value": 0}


def card(kind: str = "panel"):
    """Bordered container with a stable CSS hook (`st-key-sm-card-N`).

    Streamlit >= 1.5x no longer renders `stVerticalBlockBorderWrapper`, so styling
    bordered containers needs an explicit key-derived class.
    """
    _card_counter["value"] += 1
    return st.container(border=True, key=f"sm-card-{kind}-{_card_counter['value']}")


THEME_CSS_PATH = Path(__file__).resolve().parent / "assets" / "theme.css"


def inject_theme(logo_path: str | Path | None = None) -> None:
    _card_counter["value"] = 0
    css = THEME_CSS_PATH.read_text(encoding="utf-8")
    logo_data_uri = _image_to_data_uri(logo_path) if logo_path else ""
    if logo_data_uri:
        css = css.replace(
            "/*SIDEBAR_LOGO*/",
            ".sidebar-brand-mark { background: url('" + logo_data_uri + "') center / contain no-repeat; }",
        )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_palette_hero(
    logo_path: str | Path | None,
    profile_sentence: str,
    palette: list[tuple[str, str]],
    status: str = "",
) -> None:
    """Hero = the person's recommended palette as fabric swatches (the page's one signature moment)."""
    enter_class = "" if st.session_state.get("_sm_hero_seen") else " sm-enter"
    st.session_state["_sm_hero_seen"] = True
    logo_data_uri = _image_to_data_uri(logo_path) if logo_path else ""
    logo = f'<img src="{logo_data_uri}" alt="" />' if logo_data_uri else ""
    swatches = "".join(
        f'<div class="sm-swatch" style="--c:{escape(hex_value)};--i:{index}">'
        f'<div class="sm-swatch-cloth"></div>'
        f'<div class="sm-swatch-name">{escape(humanize_value(name))}</div></div>'
        for index, (name, hex_value) in enumerate(palette)
    )
    status_html = f'<div class="sm-status">{escape(status)}</div>' if status else ""
    st.markdown(
        f'<section class="sm-hero{enter_class}">'
        f'<div class="sm-hero-mark">{logo}<span class="sm-wordmark">StyleMatch</span></div>'
        '<h1 class="sm-hero-title">Your palette</h1>'
        f'<p class="sm-hero-lede">{profile_sentence}</p>'
        f'<div class="sm-swatches" style="--n:{max(len(palette), 1)}" aria-label="Recommended colours">{swatches}</div>'
        f"{status_html}</section>",
        unsafe_allow_html=True,
    )


def render_branded_header(logo_path: str | Path | None, title: str, subtitle: str) -> None:
    logo_markup = ""
    logo_data_uri = _image_to_data_uri(logo_path) if logo_path else ""
    if logo_data_uri:
        logo_markup = f'<img src="{logo_data_uri}" alt="{escape(title)} logo" class="brand-logo" />'

    enter_class = "" if st.session_state.get("_sm_hero_seen") else " sm-enter"
    st.session_state["_sm_hero_seen"] = True
    st.markdown(
        (
            f'<section class="brand-shell{enter_class}">{logo_markup}'
            '<div class="brand-kicker">Tone-Aware Styling</div>'
            f'<h1 class="brand-title">{escape(title)}</h1>'
            f'<p class="brand-subtitle">{escape(subtitle)}</p>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_brand(logo_path: str | Path | None, title: str, subtitle: str) -> None:
    logo_block = '<div class="sidebar-brand-mark"></div>' if logo_path else ""
    st.markdown(
        (
            f'<div class="sidebar-brand">{logo_block}'
            '<div class="sidebar-brand-copy">'
            f'<div class="sidebar-brand-title">{escape(title)}</div>'
            f'<div class="sidebar-brand-subtitle">{escape(subtitle)}</div>'
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )


def render_look_strip(
    index: int,
    score: int,
    harmony: str,
    pieces: list[tuple[str, str, str]],
    reasons: list[str],
) -> None:
    """A generated look as garment swatches (same visual language as the hero palette)."""
    cloth = "".join(
        f'<div class="sm-look-piece"><div class="sm-look-cloth" style="--c:{escape(hex_value)}"></div>'
        f'<div class="sm-look-garment">{escape(garment)}</div>'
        f'<div class="sm-look-colour">{escape(humanize_value(color))}</div></div>'
        for garment, color, hex_value in pieces
    )
    reason_items = "".join(f"<li>{escape(reason)}</li>" for reason in reasons if reason)
    st.markdown(
        f'<div class="sm-look"><div class="sm-look-head"><h3 class="panel-title">Look {index}</h3>'
        f'<div class="sm-look-score"><span>{int(score)}</span>/100</div></div>'
        f'<div class="sm-look-harmony">{escape(harmony)} harmony</div>'
        f'<div class="sm-look-strip" style="--n:{len(pieces)}">{cloth}</div>'
        f'<ul class="sm-look-reasons">{reason_items}</ul></div>',
        unsafe_allow_html=True,
    )


def render_section_intro(eyebrow: str, title: str, copy: str) -> None:
    copy_html = f'<div class="section-copy">{escape(copy)}</div>' if copy else ""
    st.markdown(f'<h2 class="section-title">{escape(title)}</h2>{copy_html}', unsafe_allow_html=True)


def render_panel_heading(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="panel-heading"><h3 class="panel-title">{escape(title)}</h3>'
        f'<p class="panel-copy">{escape(copy)}</p></div>',
        unsafe_allow_html=True,
    )


def render_profile_band(items: dict[str, str]) -> None:
    pills = []
    for label, value in items.items():
        pills.append(
            f'<div class="profile-pill"><div class="profile-pill-label">{escape(label)}</div><div class="profile-pill-value">{escape(humanize_value(value))}</div></div>'
        )
    st.markdown(f'<div class="profile-band">{"".join(pills)}</div>', unsafe_allow_html=True)


def render_welcome_card(name: str) -> None:
    st.markdown(
        (
            '<div class="welcome-card">'
            '<div class="welcome-copy">'
            '<div class="welcome-kicker">Account</div>'
            f'<h2 class="welcome-title">Welcome back, {escape(name)}</h2>'
            '<div class="welcome-subtitle">Your saved looks and synced styling history are ready.</div>'
            '</div>'
            '<div class="welcome-badge">Signed In</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_note_chip(text: str) -> None:
    st.markdown(f'<div class="note-chip">{escape(text)}</div>', unsafe_allow_html=True)


def render_sidebar_group_intro(title: str, copy: str) -> None:
    st.markdown(f'<div class="sidebar-group-label">{escape(title)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-control-copy">{escape(copy)}</div>', unsafe_allow_html=True)


def render_skin_tone_picker(options: list[str], session_key: str) -> str:
    cards = []
    for option in options:
        cards.append(
            f'<div class="sidebar-swatch-card"><div class="sidebar-swatch-head">'
            f'<span class="sidebar-swatch-dot" style="background:{SKIN_TONE_SWATCHES[option]};"></span>'
            f'<span class="sidebar-swatch-label">{escape(SKIN_TONE_LABELS[option])}</span>'
            "</div></div>"
        )
    tone_rules = "".join(
        f'.st-key-{session_key}_{option}_{i // 2} button {{ --tone: {SKIN_TONE_SWATCHES[option]}; }}'
        for i, option in enumerate(options)
    )
    st.markdown(f"<style>{tone_rules}</style>", unsafe_allow_html=True)

    current = st.session_state.get(session_key, options[0])
    rows = [options[i:i + 2] for i in range(0, len(options), 2)]
    for row_index, row in enumerate(rows):
        cols = st.columns(len(row))
        for col, option in zip(cols, row):
            with col:
                if st.button(
                    SKIN_TONE_LABELS[option],
                    key=f"{session_key}_{option}_{row_index}",
                    type="primary" if current == option else "secondary",
                    width="stretch",
                ):
                    st.session_state[session_key] = option
                    current = option
    return current


def render_icon_choice_group(
    options: list[str],
    session_key: str,
    meta: dict[str, tuple[str, str]],
    columns_per_row: int = 2,
) -> str:
    current = st.session_state.get(session_key, options[0])
    rows = [options[i:i + columns_per_row] for i in range(0, len(options), columns_per_row)]
    for row_index, row in enumerate(rows):
        cols = st.columns(len(row))
        for col, option in zip(cols, row):
            with col:
                if st.button(
                    choice_label(option, meta),
                    key=f"{session_key}_{option}_{row_index}",
                    type="primary" if current == option else "secondary",
                    width="stretch",
                ):
                    st.session_state[session_key] = option
                    current = option
    return current


def render_color_select(label: str, options: list[str], selected: str, key: str, color_map: dict[str, str]) -> str:
    if key in st.session_state and st.session_state[key] in options:
        selected = st.session_state[key]
    elif key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    color_hex = color_map.get(selected, "#808080")
    st.markdown(
        f'<div class="color-field-label"><span class="current-color-dot" style="background:{escape(color_hex)};"></span>{escape(label)}</div>',
        unsafe_allow_html=True,
    )
    return st.selectbox(
        label,
        options,
        index=options.index(selected),
        key=key,
        format_func=humanize_value,
        label_visibility="collapsed",
    )


def render_color_legend(
    title: str,
    colors: list[str],
    muted: bool = False,
    color_map: dict[str, str] | None = None,
) -> None:
    st.markdown(f'<div class="legend-title">{escape(title)}</div>', unsafe_allow_html=True)
    if not colors:
        st.caption("No items to show.")
        return

    chip_class = "legend-chip legend-chip-muted" if muted else "legend-chip"
    chips = []
    for color in colors:
        dot_style = ""
        if color_map and color in color_map:
            dot_style = f' style="background:{escape(color_map[color])};"'
        chips.append(
            f'<div class="{chip_class}"><span class="legend-dot"{dot_style}></span>{escape(humanize_value(color))}</div>'
        )
    st.markdown(f'<div class="legend-row">{"".join(chips)}</div>', unsafe_allow_html=True)


def render_score_badge(score: int) -> None:
    score = max(0, min(int(score), 100))
    if score >= 85:
        label, tier = "Editorial match", "top"
    elif score >= 70:
        label, tier = "Strong harmony", "mid"
    elif score >= 55:
        label, tier = "Balanced option", "mid"
    else:
        label, tier = "Needs refining", "low"

    st.markdown(
        f"""
        <div class="score-shell" data-tier="{tier}">
            <div class="score-label">Outfit Match</div>
            <div class="score-topline">
                <div class="score-value">{score}<span style="font-size:1.1rem;color:var(--sm-muted);">/100</span></div>
                <div class="score-note">{escape(label)}</div>
            </div>
            <div class="score-rail" aria-hidden="true">
                <div class="score-fill" style="width:{score}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

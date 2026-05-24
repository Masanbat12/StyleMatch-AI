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


def inject_theme(logo_path: str | Path | None = None) -> None:
    logo_data_uri = _image_to_data_uri(logo_path) if logo_path else ""
    sidebar_logo_rule = ""
    if logo_data_uri:
        sidebar_logo_rule = f"""
        .sidebar-brand-mark {{
            background-image: url('{logo_data_uri}');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }}
        """

    st.markdown(
        f"""
        <style>
        :root {{
            --sm-bg: #f5efe6;
            --sm-surface: rgba(255, 252, 247, 0.88);
            --sm-sidebar: #15110f;
            --sm-ink: #261f1a;
            --sm-muted: #7b6b5d;
            --sm-gold: #c8a96a;
            --sm-gold-deep: #9f7d42;
            --sm-shadow: 0 18px 40px rgba(38, 31, 26, 0.08);
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(210, 182, 130, 0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(204, 189, 162, 0.20), transparent 22%),
                linear-gradient(180deg, #fbf8f3 0%, var(--sm-bg) 100%);
            color: var(--sm-ink);
        }}

        .block-container {{
            max-width: 1280px;
            padding-top: 1.8rem;
            padding-bottom: 3.2rem;
            padding-left: 2.2rem;
            padding-right: 2.2rem;
        }}

        [data-testid="stSidebar"] {{
            background:
                radial-gradient(circle at top, rgba(200, 169, 106, 0.18), transparent 24%),
                linear-gradient(180deg, var(--sm-sidebar) 0%, #120f0d 100%);
            border-right: 1px solid rgba(228, 205, 167, 0.12);
            min-width: 340px !important;
            max-width: 340px !important;
        }}

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption {{
            color: #f4eadb !important;
        }}

        [data-testid="stSidebar"] .stCaption {{
            color: rgba(244, 234, 219, 0.72) !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] textarea {{
            background: rgba(255, 250, 243, 0.07) !important;
            border: 1px solid rgba(228, 205, 167, 0.16) !important;
            border-radius: 16px !important;
            box-shadow: none !important;
            color: #fff7ec !important;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            min-height: 2.95rem;
            border-radius: 16px;
            font-weight: 700;
            font-size: 0.90rem;
            padding: 0.5rem 0.7rem;
            white-space: nowrap;
            line-height: 1.1;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 0.95rem;
            padding: 0.4rem 0 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(228, 205, 167, 0.12);
        }}

        .sidebar-brand-mark {{
            width: 54px;
            height: 54px;
            border-radius: 18px;
            background-color: rgba(255, 250, 243, 0.06);
            box-shadow: inset 0 0 0 1px rgba(228, 205, 167, 0.08);
            flex: 0 0 auto;
        }}

        {sidebar_logo_rule}

        .sidebar-brand-copy {{
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }}

        .sidebar-brand-title {{
            color: #fff8eb;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.02rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .sidebar-brand-subtitle {{
            color: rgba(244, 234, 219, 0.72);
            font-size: 0.82rem;
        }}

        .sidebar-group-label {{
            margin-top: 1.35rem;
            margin-bottom: 0.5rem;
            color: #d8c39d;
            font-size: 0.78rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
        }}

        .sidebar-control-copy {{
            color: rgba(244, 234, 219, 0.74);
            font-size: 0.8rem;
            line-height: 1.45;
            margin: 0 0 0.7rem;
        }}

        .sidebar-swatch-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}

        .sidebar-swatch-card {{
            background: rgba(255, 250, 243, 0.05);
            border: 1px solid rgba(228, 205, 167, 0.14);
            border-radius: 16px;
            padding: 0.62rem 0.72rem;
        }}

        .sidebar-swatch-head {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
        }}

        .sidebar-swatch-dot {{
            width: 16px;
            height: 16px;
            border-radius: 999px;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.18), 0 4px 10px rgba(0,0,0,0.18);
            flex: 0 0 auto;
        }}

        .sidebar-swatch-label {{
            color: #fff4e5;
            font-size: 0.88rem;
            font-weight: 600;
            white-space: nowrap;
        }}

        .sidebar-chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-bottom: 0.6rem;
        }}

        .sidebar-chip-note {{
            color: rgba(244, 234, 219, 0.62);
            font-size: 0.78rem;
            margin-top: -0.15rem;
            margin-bottom: 0.6rem;
        }}

        .brand-shell {{
            background: linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(250, 244, 235, 0.82));
            border: 1px solid rgba(200, 169, 106, 0.18);
            border-radius: 32px;
            padding: 1.45rem 2rem 1.25rem;
            box-shadow: var(--sm-shadow);
            text-align: center;
            margin: 0 auto 1.1rem;
            max-width: 920px;
            position: relative;
            overflow: hidden;
        }}

        .brand-shell::before {{
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at top center, rgba(200, 169, 106, 0.12), transparent 30%),
                linear-gradient(135deg, rgba(255, 255, 255, 0.48), transparent 55%);
            pointer-events: none;
        }}

        .brand-logo {{
            width: min(82px, 24vw);
            height: auto;
            margin: 0 auto 0.75rem;
            display: block;
            filter: drop-shadow(0 10px 16px rgba(39, 29, 18, 0.08));
        }}

        .brand-kicker {{
            color: var(--sm-gold-deep);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }}

        .brand-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: clamp(2rem, 4vw, 3.25rem);
            line-height: 1.04;
            margin: 0;
        }}

        .brand-subtitle {{
            max-width: 560px;
            margin: 0.55rem auto 0;
            color: var(--sm-muted);
            font-size: 0.95rem;
            line-height: 1.55;
        }}

        .profile-band {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin: 0.35rem 0 1.35rem;
        }}

        .profile-pill {{
            background: rgba(255, 250, 243, 0.76);
            border: 1px solid rgba(200, 169, 106, 0.16);
            border-radius: 999px;
            padding: 0.62rem 0.95rem;
            box-shadow: 0 10px 24px rgba(38, 31, 26, 0.05);
            min-width: 146px;
            white-space: nowrap;
        }}

        .profile-pill-label {{
            color: var(--sm-gold-deep);
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.18rem;
        }}

        .profile-pill-value {{
            color: var(--sm-ink);
            font-weight: 600;
            text-transform: capitalize;
            white-space: nowrap;
        }}

        .welcome-card {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1rem 1.15rem;
            margin: 0.2rem 0 1rem;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(255, 250, 243, 0.94), rgba(245, 235, 214, 0.88));
            border: 1px solid rgba(200, 169, 106, 0.18);
            box-shadow: 0 14px 30px rgba(38, 31, 26, 0.06);
        }}

        .welcome-copy {{
            min-width: 0;
        }}

        .welcome-kicker {{
            color: var(--sm-gold-deep);
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.22rem;
        }}

        .welcome-title {{
            color: var(--sm-ink);
            font-family: Georgia, "Times New Roman", serif;
            font-size: clamp(1.2rem, 2.2vw, 1.55rem);
            line-height: 1.15;
            margin: 0;
        }}

        .welcome-subtitle {{
            color: var(--sm-muted);
            margin-top: 0.3rem;
            font-size: 0.92rem;
            line-height: 1.55;
        }}

        .welcome-badge {{
            flex: 0 0 auto;
            border-radius: 999px;
            padding: 0.48rem 0.85rem;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(200, 169, 106, 0.2);
            color: var(--sm-gold-deep);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            white-space: nowrap;
        }}

        .section-kicker {{
            color: var(--sm-gold-deep);
            font-size: 0.78rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}

        .section-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: clamp(1.55rem, 2vw, 2.2rem);
            line-height: 1.08;
            margin-bottom: 0.45rem;
        }}

        .section-copy {{
            color: var(--sm-muted);
            max-width: 760px;
            line-height: 1.7;
            margin-bottom: 0.4rem;
        }}

        .panel-heading {{
            margin-bottom: 1rem;
        }}

        .panel-eyebrow {{
            color: var(--sm-gold-deep);
            font-size: 0.74rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }}

        .panel-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.32rem;
            margin-bottom: 0.25rem;
        }}

        .panel-copy {{
            color: var(--sm-muted);
            line-height: 1.6;
            margin-bottom: 0;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: var(--sm-surface);
            border: 1px solid rgba(200, 169, 106, 0.16);
            border-radius: 28px;
            padding: 0.45rem 0.4rem;
            box-shadow: var(--sm-shadow);
            backdrop-filter: blur(8px);
        }}

        div[data-baseweb="tab-list"] {{
            gap: 0.55rem;
            background: rgba(255, 250, 243, 0.72);
            border: 1px solid rgba(200, 169, 106, 0.16);
            border-radius: 999px;
            padding: 0.35rem;
            box-shadow: 0 12px 24px rgba(38, 31, 26, 0.05);
            width: fit-content;
        }}

        button[data-baseweb="tab"] {{
            border-radius: 999px !important;
            color: var(--sm-muted) !important;
            font-weight: 600 !important;
            min-height: 2.7rem !important;
            padding: 0 1.15rem !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] {{
            background: linear-gradient(135deg, #f0d59d 0%, #c7a05b 100%) !important;
            color: #241b13 !important;
            box-shadow: 0 10px 18px rgba(163, 126, 59, 0.26);
        }}

        [data-testid="stFileUploaderDropzone"] {{
            border-radius: 24px !important;
            border: 1.5px dashed rgba(200, 169, 106, 0.42) !important;
            background: linear-gradient(180deg, rgba(255, 250, 243, 0.90), rgba(249, 241, 229, 0.86)) !important;
            padding: 1.2rem !important;
        }}

        .stButton > button {{
            border-radius: 999px;
            border: none;
            background: linear-gradient(135deg, #edd39a 0%, #c7a05b 100%);
            color: #241b13;
            font-weight: 700;
            padding: 0.7rem 1.4rem;
            box-shadow: 0 10px 22px rgba(163, 126, 59, 0.24);
            white-space: nowrap;
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 14px 26px rgba(163, 126, 59, 0.30);
        }}

        div[data-baseweb="select"] > div,
        .stTextArea textarea {{
            border-radius: 16px !important;
            border: 1px solid rgba(200, 169, 106, 0.18) !important;
            background: rgba(255, 255, 255, 0.88) !important;
            min-height: 3rem;
        }}

        .legend-title {{
            color: var(--sm-gold-deep);
            font-size: 0.76rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.7rem;
        }}

        .legend-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-bottom: 0.2rem;
        }}

        .legend-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.58rem 0.95rem;
            border-radius: 999px;
            border: 1px solid rgba(200, 169, 106, 0.18);
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 10px 22px rgba(38, 31, 26, 0.04);
            font-size: 0.92rem;
            color: var(--sm-ink);
            text-transform: capitalize;
        }}

        .legend-chip-muted {{
            border-style: dashed;
            color: var(--sm-muted);
            background: rgba(248, 242, 234, 0.86);
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: linear-gradient(135deg, #e5c98f, #c09a56);
        }}

        .color-field-label {{
            color: var(--sm-gold-deep);
            font-size: 0.76rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.38rem;
        }}

        .current-color-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.58rem 0.9rem;
            border-radius: 999px;
            background: rgba(255, 250, 243, 0.88);
            border: 1px solid rgba(200, 169, 106, 0.18);
            margin-bottom: 0.55rem;
            color: var(--sm-ink);
            font-weight: 600;
        }}

        .current-color-dot {{
            width: 12px;
            height: 12px;
            border-radius: 999px;
            border: 1px solid rgba(38, 31, 26, 0.14);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.45);
        }}

        .score-shell {{
            border-radius: 26px;
            padding: 1.05rem 1.1rem 1rem;
            background: linear-gradient(180deg, rgba(255, 250, 243, 0.94), rgba(247, 238, 224, 0.86));
            border: 1px solid rgba(200, 169, 106, 0.18);
            margin: 0.55rem 0 1rem;
        }}

        .score-label {{
            color: var(--sm-gold-deep);
            font-size: 0.76rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }}

        .score-topline {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
            margin-bottom: 0.7rem;
        }}

        .score-value {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2.2rem;
            line-height: 1;
            color: var(--sm-ink);
        }}

        .score-note {{
            color: var(--sm-muted);
            font-weight: 600;
        }}

        .score-rail {{
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(152, 122, 74, 0.12);
            overflow: hidden;
        }}

        .score-fill {{
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #efd8a7 0%, #c7a05b 100%);
        }}

        .note-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            border-radius: 999px;
            padding: 0.5rem 0.85rem;
            background: rgba(255, 248, 236, 0.86);
            border: 1px solid rgba(200, 169, 106, 0.15);
            color: var(--sm-muted);
            font-size: 0.9rem;
        }}

        .avatar-caption {{
            color: var(--sm-muted);
            text-align: center;
            margin-top: 0.5rem;
            font-size: 0.92rem;
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}

            .sidebar-swatch-grid {{
                grid-template-columns: 1fr;
            }}

            .brand-shell {{
                padding: 1.2rem 1.15rem 1.05rem;
                border-radius: 24px;
            }}

            .brand-logo {{
                width: min(72px, 22vw);
                margin-bottom: 0.65rem;
            }}

            .brand-title {{
                font-size: clamp(1.85rem, 8vw, 2.4rem);
            }}

            .brand-subtitle {{
                font-size: 0.92rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_branded_header(logo_path: str | Path | None, title: str, subtitle: str) -> None:
    logo_markup = ""
    logo_data_uri = _image_to_data_uri(logo_path) if logo_path else ""
    if logo_data_uri:
        logo_markup = f'<img src="{logo_data_uri}" alt="{escape(title)} logo" class="brand-logo" />'

    st.markdown(
        (
            f'<section class="brand-shell">{logo_markup}'
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


def render_section_intro(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="section-kicker">{escape(eyebrow)}</div>'
        f'<div class="section-title">{escape(title)}</div>'
        f'<div class="section-copy">{escape(copy)}</div>',
        unsafe_allow_html=True,
    )


def render_panel_heading(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="panel-heading"><div class="panel-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="panel-title">{escape(title)}</div><p class="panel-copy">{escape(copy)}</p></div>',
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
    st.markdown(f'<div class="sidebar-swatch-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

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
                    use_container_width=True,
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
                    use_container_width=True,
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
        f'<div class="color-field-label">{escape(label)}</div>'
        f'<div class="current-color-chip"><span class="current-color-dot" style="background:{escape(color_hex)};"></span>{escape(humanize_value(selected))}</div>',
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
    if score >= 85:
        label = "Editorial match"
    elif score >= 70:
        label = "Strong harmony"
    elif score >= 55:
        label = "Balanced option"
    else:
        label = "Needs refining"

    st.markdown(
        f"""
        <div class="score-shell">
            <div class="score-label">Outfit Match</div>
            <div class="score-topline">
                <div class="score-value">{score}<span style="font-size:1.1rem;color:var(--sm-muted);">/100</span></div>
                <div class="score-note">{escape(label)}</div>
            </div>
            <div class="score-rail">
                <div class="score-fill" style="width:{max(0, min(score, 100))}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

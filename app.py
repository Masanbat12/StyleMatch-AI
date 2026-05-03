from __future__ import annotations

from pathlib import Path

import streamlit as st

from avatar_renderer import render_avatar
from catalog import ALL_COLORS, COLOR_MAP, OCCASION_OPTIONS, STYLE_OPTIONS, UNDERTONE_OPTIONS
from database import get_saved_outfits, init_db, save_outfit
from image_analysis import ImageAnalysisError, analyze_skin_from_upload
from knowledge_base import SOURCES
from recommendation_engine import generate_outfit_suggestions, get_avoid_colors, get_recommended_colors, score_breakdown
from style_assistant import build_grounded_answer
from ui_components import (
    OCCASION_META,
    STYLE_META,
    UNDERTONE_META,
    humanize_value,
    inject_theme,
    render_branded_header,
    render_color_legend,
    render_color_select,
    render_icon_choice_group,
    render_note_chip,
    render_panel_heading,
    render_profile_band,
    render_score_badge,
    render_section_intro,
    render_sidebar_brand,
    render_sidebar_group_intro,
    render_skin_tone_picker,
)

DEFAULT_PROFILE = {
    "skin_tone": "medium",
    "undertone": "neutral",
    "style": "casual",
    "occasion": "daily",
}

UI_SKIN_TONE_OPTIONS = ["fair", "light", "light_medium", "medium", "tan", "deep_tan", "dark"]
ROOT_DIR = Path(__file__).resolve().parent
LOGO_PATH = ROOT_DIR / "assets" / "logo.png"


def normalize_skin_tone(value: str) -> str:
    if value == "very_fair":
        return "fair"
    if value == "deep_dark":
        return "dark"
    return value

init_db()

st.set_page_config(
    page_title="StyleMatch AI",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "👕",
    layout="wide",
)
inject_theme(LOGO_PATH if LOGO_PATH.exists() else None)

for key, default_value in DEFAULT_PROFILE.items():
    st.session_state.setdefault(key, default_value)

st.session_state.skin_tone = normalize_skin_tone(st.session_state.skin_tone)

with st.sidebar:
    render_sidebar_brand(
        LOGO_PATH if LOGO_PATH.exists() else None,
        "StyleMatch AI",
        "Profile atelier controls",
    )
    st.caption("Set complexion, mood, and occasion with a cleaner styling workflow.")

    render_sidebar_group_intro(
        "Complexion",
        "Choose a tone and undertone to anchor the styling direction.",
    )
    st.session_state.skin_tone = render_skin_tone_picker(UI_SKIN_TONE_OPTIONS, "skin_tone")
    st.session_state.undertone = render_icon_choice_group(UNDERTONE_OPTIONS, "undertone", UNDERTONE_META, columns_per_row=1)

    render_sidebar_group_intro(
        "Wardrobe Direction",
        "Choose the aesthetic and setting to refine the recommendations.",
    )
    st.session_state.style = render_icon_choice_group(STYLE_OPTIONS, "style", STYLE_META, columns_per_row=2)
    st.session_state.occasion = render_icon_choice_group(OCCASION_OPTIONS, "occasion", OCCASION_META, columns_per_row=2)

skin_tone = st.session_state.skin_tone
undertone = st.session_state.undertone
style = st.session_state.style
occasion = st.session_state.occasion

recommended_colors = get_recommended_colors(undertone, style, occasion)
avoid_colors = get_avoid_colors(undertone)

render_branded_header(
    LOGO_PATH if LOGO_PATH.exists() else None,
    "StyleMatch AI",
    "Refined outfit guidance for tone, style, and occasion.",
)
render_profile_band(
    {
        "Skin Tone": skin_tone,
        "Undertone": undertone,
        "Style": style,
        "Occasion": occasion,
    }
)

tab_analyzer, tab_builder, tab_generator, tab_assistant, tab_saved, tab_sources = st.tabs(
    ["Image Analyzer", "Outfit Builder", "Generate 5 Looks", "AI Style Assistant", "Saved Looks", "Sources"]
)

with tab_analyzer:
    render_section_intro(
        "Image Atelier",
        "Profile your complexion with a polished upload workflow",
        "Drop in a well-lit portrait to estimate skin tone and undertone, then carry that profile straight into the recommendation engine.",
    )
    with st.container(border=True):
        render_panel_heading(
            "Upload Studio",
            "Analyze a front-facing portrait",
            "Use natural lighting and a clear frontal angle for the most grounded result.",
        )
        render_note_chip("Supported formats: PNG, JPG, JPEG")
        uploaded_file = st.file_uploader("Upload a clear front-facing image", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            result = analyze_skin_from_upload(uploaded_file)
        except ImageAnalysisError as exc:
            st.error(str(exc))
        except Exception:
            st.error("The image could not be analyzed. Please try a different photo.")
        else:
            info_col, image_col = st.columns([1, 1], gap="large")

            with info_col:
                with st.container(border=True):
                    render_panel_heading(
                        "Detected Profile",
                        "Your complexion summary",
                        "Use the detected profile directly in the styling flow, while keeping an eye on the reliability read below.",
                    )
                    if result["confidence_label"] == "high":
                        st.success("Analysis complete")
                    elif result["confidence_label"] == "medium":
                        st.warning("Best estimate under moderately noisy lighting")
                    else:
                        st.error("Low-confidence estimate")

                    st.write(f"**Estimated skin tone:** {humanize_value(result['skin_tone'])}")
                    st.write(f"**Estimated undertone:** {humanize_value(result['undertone'])}")
                    st.write(
                        f"**Confidence:** {int(result['confidence'] * 100)}% ({humanize_value(result['confidence_label'])})"
                    )
                    st.write(f"**Dominant skin hex:** {result['dominant_skin_hex']}")
                    st.write(f"**Brightness score:** {result['brightness']}")
                    st.write(f"**Reliable skin samples:** {result['sample_pixel_count']}")
                    st.caption(result["note"])

                    if result["warnings"]:
                        st.markdown("**Quality warnings**")
                        for warning in result["warnings"]:
                            st.write(f"- {warning}")

                    if st.button("Use detected profile", key="use_detected_profile"):
                        st.session_state.skin_tone = normalize_skin_tone(result["skin_tone"])
                        st.session_state.undertone = result["undertone"]
                        st.rerun()

            with image_col:
                with st.container(border=True):
                    render_panel_heading(
                        "Visual Read",
                        "Uploaded reference and swatch",
                        "A quick visual confirmation of the photo used and the sampled complexion color.",
                    )
                    st.image(result["preview_image"], caption="Uploaded image", width="stretch")
                    st.image(result["swatch_image"], caption="Detected skin color swatch", width="content")

with tab_builder:
    render_section_intro(
        "Style Studio",
        "Build a refined look with premium wardrobe controls",
        "Dial in shirt, pants, and shoes while the engine explains why the palette works with your undertone and context.",
    )
    left_col, right_col = st.columns([1.06, 0.94], gap="large")

    with left_col:
        with st.container(border=True):
            render_panel_heading(
                "Curate",
                "Design your outfit combination",
                "Start with recommended tones, then push the palette toward a more editorial direction if you want to experiment.",
            )
            shirt_options = recommended_colors + [color for color in ALL_COLORS if color not in recommended_colors]
            shirt_color = render_color_select("Shirt Color", shirt_options, shirt_options[0], "builder_shirt_color", COLOR_MAP)
            pants_color = render_color_select("Pants Color", ALL_COLORS, "black", "builder_pants_color", COLOR_MAP)
            shoes_color = render_color_select("Shoes Color", ALL_COLORS, "white", "builder_shoes_color", COLOR_MAP)

            score, reasons = score_breakdown(
                skin_tone=skin_tone,
                undertone=undertone,
                style=style,
                occasion=occasion,
                shirt_color=shirt_color,
                pants_color=pants_color,
                shoes_color=shoes_color,
            )

            render_score_badge(score)
            render_color_legend("Recommended palette", recommended_colors, color_map=COLOR_MAP)
            render_color_legend("Lower-priority colors", avoid_colors, muted=True, color_map=COLOR_MAP)

            st.markdown("#### Why this score?")
            for reason in reasons:
                st.write(f"- {reason}")

            if st.button("Save this outfit", use_container_width=True):
                save_outfit(
                    skin_tone=skin_tone,
                    undertone=undertone,
                    style=style,
                    occasion=occasion,
                    shirt_color=shirt_color,
                    pants_color=pants_color,
                    shoes_color=shoes_color,
                    score=score,
                )
                st.success("Outfit saved successfully.")

    with right_col:
        with st.container(border=True):
            render_panel_heading(
                "Avatar Preview",
                "See the silhouette in context",
                "A premium preview card for checking balance, contrast, and how the pieces land together visually.",
            )
            avatar = render_avatar(
                skin_tone=skin_tone,
                shirt_color=shirt_color,
                pants_color=pants_color,
                shoes_color=shoes_color,
            )
            st.image(avatar, width="content")
            st.markdown('<div class="avatar-caption">Rendered from layered fashion assets tinted to your current outfit selection.</div>', unsafe_allow_html=True)

with tab_generator:
    render_section_intro(
        "Look Generator",
        "Generate fast, premium-ready outfit directions",
        "Explore automatically composed looks ranked by harmony, versatility, and contrast so you can shortlist ideas quickly.",
    )
    suggestions = generate_outfit_suggestions(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        limit=5,
    )

    if suggestions:
        featured = suggestions[0]
        hero_col, summary_col = st.columns([0.88, 1.12], gap="large")

        with hero_col:
            with st.container(border=True):
                render_panel_heading(
                    "Featured Avatar",
                    "Top-ranked generated look",
                    "Preview the strongest combination first, then compare the full set of five recommendations beside it.",
                )
                featured_avatar = render_avatar(
                    skin_tone=skin_tone,
                    shirt_color=featured["shirt_color"],
                    pants_color=featured["pants_color"],
                    shoes_color=featured["shoes_color"],
                    width=330,
                    height=500,
                )
                st.image(featured_avatar, width="content")
                render_score_badge(featured["score"])
                st.caption(featured["explanation"])

        with summary_col:
            for idx, outfit in enumerate(suggestions, start=1):
                with st.container(border=True):
                    render_panel_heading(
                        f"Look {idx}",
                        f"{humanize_value(outfit['shirt_color'])}, {humanize_value(outfit['pants_color'])}, {humanize_value(outfit['shoes_color'])}",
                        f"{humanize_value(outfit['harmony'])} harmony with a {outfit['score']}/100 match score.",
                    )
                    st.write(f"**Shirt:** {humanize_value(outfit['shirt_color'])}")
                    st.write(f"**Pants:** {humanize_value(outfit['pants_color'])}")
                    st.write(f"**Shoes:** {humanize_value(outfit['shoes_color'])}")
                    st.caption(outfit["explanation"])
                    for reason in outfit.get("reasons", [])[:2]:
                        st.write(f"- {reason}")
                    if st.button(f"Save Look {idx}", key=f"save_generated_{idx}"):
                        save_outfit(
                            skin_tone=skin_tone,
                            undertone=undertone,
                            style=style,
                            occasion=occasion,
                            shirt_color=outfit["shirt_color"],
                            pants_color=outfit["pants_color"],
                            shoes_color=outfit["shoes_color"],
                            score=outfit["score"],
                        )
                        st.success(f"Look {idx} saved.")

with tab_assistant:
    render_section_intro(
        "AI Concierge",
        "Ask for grounded wardrobe direction",
        "Turn your current profile into styling guidance for dates, work looks, evening dressing, or a more defined personal aesthetic.",
    )
    with st.container(border=True):
        render_panel_heading(
            "Prompt",
            "Describe the moment you are dressing for",
            "The assistant stays grounded in the project knowledge base and your active profile settings.",
        )
        question = st.text_area(
            "Ask something like: What should I wear for a date tonight?",
            value="What should I wear for this occasion?",
            height=120,
        )

        if st.button("Generate grounded advice", key="ask_assistant"):
            answer = build_grounded_answer(
                skin_tone=skin_tone,
                undertone=undertone,
                style=style,
                occasion=occasion,
                user_prompt=question,
            )
            st.text_area("Assistant answer", value=answer, height=420)

with tab_saved:
    render_section_intro(
        "Saved Looks",
        "Review your archived outfit decisions",
        "A running wardrobe history of combinations you chose to keep, complete with profile context and avatar previews.",
    )
    saved_outfits = get_saved_outfits()

    if not saved_outfits:
        st.info("No saved outfits yet.")
    else:
        for outfit in saved_outfits:
            with st.expander(f"Look #{outfit['id']} - {outfit['score']}/100"):
                meta_col, preview_col = st.columns([1.1, 0.9], gap="large")

                with meta_col:
                    render_panel_heading(
                        "Saved Profile",
                        f"Look #{outfit['id']}",
                        "Stored locally so you can revisit combinations that felt right.",
                    )
                    st.write(f"**Skin tone:** {humanize_value(outfit['skin_tone'])}")
                    st.write(f"**Undertone:** {humanize_value(outfit['undertone'])}")
                    st.write(f"**Style:** {humanize_value(outfit['style'])}")
                    st.write(f"**Occasion:** {humanize_value(outfit['occasion'])}")
                    st.write(f"**Shirt:** {humanize_value(outfit['shirt_color'])}")
                    st.write(f"**Pants:** {humanize_value(outfit['pants_color'])}")
                    st.write(f"**Shoes:** {humanize_value(outfit['shoes_color'])}")
                    st.caption(f"Saved at: {outfit['created_at']}")

                with preview_col:
                    saved_avatar = render_avatar(
                        skin_tone=normalize_skin_tone(outfit["skin_tone"]),
                        shirt_color=outfit["shirt_color"],
                        pants_color=outfit["pants_color"],
                        shoes_color=outfit["shoes_color"],
                        width=280,
                        height=420,
                    )
                    st.image(saved_avatar, width="content")

with tab_sources:
    render_section_intro(
        "Knowledge Base",
        "See the grounded references behind the recommendations",
        "Each source helps keep the assistant and the palette logic tied to explicit color and styling guidance.",
    )
    for source in SOURCES:
        with st.container(border=True):
            render_panel_heading(
                "Embedded Source",
                source["title"],
                source["summary"],
            )
            st.code(source["url"], language="text")

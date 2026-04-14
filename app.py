from __future__ import annotations

import streamlit as st

from avatar_renderer import render_avatar
from database import get_saved_outfits, init_db, save_outfit
from image_analysis import analyze_skin_from_upload
from knowledge_base import SOURCES
from recommendation_engine import (
    ALL_COLORS,
    SKIN_TONE_OPTIONS,
    generate_outfit_suggestions,
    get_avoid_colors,
    get_recommended_colors,
    score_breakdown,
)
from style_assistant import build_grounded_answer
from ui_components import render_color_legend, render_score_badge

init_db()

st.set_page_config(page_title="StyleMatch AI v3", page_icon="👕", layout="wide")

if "skin_tone" not in st.session_state:
    st.session_state.skin_tone = "medium"
if "undertone" not in st.session_state:
    st.session_state.undertone = "neutral"
if "style" not in st.session_state:
    st.session_state.style = "casual"
if "occasion" not in st.session_state:
    st.session_state.occasion = "daily"

st.title("👕 StyleMatch AI v3")
st.caption("Improved grounded outfit recommendations with better skin-tone options and more realistic image analysis.")

with st.sidebar:
    st.header("Profile")
    st.session_state.skin_tone = st.selectbox("Skin tone", SKIN_TONE_OPTIONS, index=SKIN_TONE_OPTIONS.index(st.session_state.skin_tone))
    st.session_state.undertone = st.selectbox("Undertone", ["warm", "cool", "neutral"], index=["warm", "cool", "neutral"].index(st.session_state.undertone))
    st.session_state.style = st.selectbox("Style", ["casual", "elegant", "street", "minimal"], index=["casual", "elegant", "street", "minimal"].index(st.session_state.style))
    st.session_state.occasion = st.selectbox("Occasion", ["daily", "date", "work", "evening"], index=["daily", "date", "work", "evening"].index(st.session_state.occasion))

skin_tone = st.session_state.skin_tone
undertone = st.session_state.undertone
style = st.session_state.style
occasion = st.session_state.occasion

recommended_colors = get_recommended_colors(undertone, style, occasion)
avoid_colors = get_avoid_colors(undertone)

tab_analyzer, tab_builder, tab_generator, tab_assistant, tab_saved, tab_sources = st.tabs(
    ["Image Analyzer", "Outfit Builder", "Generate 5 Looks", "AI Style Assistant", "Saved Looks", "Sources"]
)

with tab_analyzer:
    st.subheader("Upload a photo to estimate skin tone and undertone")
    uploaded_file = st.file_uploader("Upload a clear front-facing image", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        result = analyze_skin_from_upload(uploaded_file)

        info_col, image_col = st.columns([1, 1])

        with info_col:
            st.success("Analysis complete")
            st.write(f"**Estimated skin tone:** {result['skin_tone']}")
            st.write(f"**Estimated undertone:** {result['undertone']}")
            st.write(f"**Dominant skin hex:** {result['dominant_skin_hex']}")
            st.write(f"**Brightness score:** {result['brightness']}")
            st.caption(result["note"])

            if st.button("Use detected profile", key="use_detected_profile"):
                st.session_state.skin_tone = result["skin_tone"]
                st.session_state.undertone = result["undertone"]
                st.rerun()

        with image_col:
            st.image(result["preview_image"], caption="Uploaded image", width="stretch")
            st.image(result["swatch_image"], caption="Detected skin color swatch", width="content")

with tab_builder:
    left_col, right_col = st.columns([1.05, 0.95])

    with left_col:
        st.subheader("Build your look")
        shirt_options = recommended_colors + [c for c in ALL_COLORS if c not in recommended_colors]
        shirt_color = st.selectbox("Shirt color", shirt_options)
        pants_color = st.selectbox("Pants color", ALL_COLORS, index=ALL_COLORS.index("black"))
        shoes_color = st.selectbox("Shoes color", ALL_COLORS, index=ALL_COLORS.index("white"))

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
        render_color_legend("Recommended colors", recommended_colors)
        render_color_legend("Less recommended", avoid_colors)

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
        st.subheader("Avatar preview")
        avatar = render_avatar(
            skin_tone=skin_tone,
            shirt_color=shirt_color,
            pants_color=pants_color,
            shoes_color=shoes_color,
        )
        st.image(avatar, width="content")

with tab_generator:
    st.subheader("Generate 5 automatic outfit ideas")
    suggestions = generate_outfit_suggestions(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        limit=5,
    )

    for idx, outfit in enumerate(suggestions, start=1):
        with st.expander(f"Look {idx} — Score {outfit['score']}/100", expanded=(idx == 1)):
            meta_col, avatar_col = st.columns([1.05, 0.95])

            with meta_col:
                st.write(f"**Shirt:** {outfit['shirt_color']}")
                st.write(f"**Pants:** {outfit['pants_color']}")
                st.write(f"**Shoes:** {outfit['shoes_color']}")
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

            with avatar_col:
                generated_avatar = render_avatar(
                    skin_tone=skin_tone,
                    shirt_color=outfit["shirt_color"],
                    pants_color=outfit["pants_color"],
                    shoes_color=outfit["shoes_color"],
                    width=300,
                    height=450,
                )
                st.image(generated_avatar, width="content")

with tab_assistant:
    st.subheader("AI Style Assistant")
    question = st.text_area(
        "Ask something like: What should I wear for a date tonight?",
        value="What should I wear for this occasion?",
        height=100,
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
    st.subheader("Saved outfits")
    saved_outfits = get_saved_outfits()

    if not saved_outfits:
        st.info("No saved outfits yet.")
    else:
        for row in saved_outfits:
            (
                outfit_id,
                saved_skin_tone,
                saved_undertone,
                saved_style,
                saved_occasion,
                saved_shirt,
                saved_pants,
                saved_shoes,
                saved_score,
            ) = row

            with st.expander(f"Look #{outfit_id} — {saved_score}/100"):
                meta_col, preview_col = st.columns([1.1, 0.9])

                with meta_col:
                    st.write(f"**Skin tone:** {saved_skin_tone}")
                    st.write(f"**Undertone:** {saved_undertone}")
                    st.write(f"**Style:** {saved_style}")
                    st.write(f"**Occasion:** {saved_occasion}")
                    st.write(f"**Shirt:** {saved_shirt}")
                    st.write(f"**Pants:** {saved_pants}")
                    st.write(f"**Shoes:** {saved_shoes}")

                with preview_col:
                    saved_avatar = render_avatar(
                        skin_tone=saved_skin_tone,
                        shirt_color=saved_shirt,
                        pants_color=saved_pants,
                        shoes_color=saved_shoes,
                        width=280,
                        height=420,
                    )
                    st.image(saved_avatar, width="content")

with tab_sources:
    st.subheader("Grounding sources used by the project")
    st.caption("These sources are embedded in the project knowledge base so the assistant and rules stay anchored.")
    for source in SOURCES:
        st.markdown(f"**{source['title']}**")
        st.write(source["summary"])
        st.code(source["url"], language="text")

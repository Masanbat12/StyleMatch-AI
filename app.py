from __future__ import annotations

import itertools
from pathlib import Path

import streamlit as st

from avatar_renderer import render_avatar
from catalog import ALL_COLORS, COLOR_MAP, OCCASION_OPTIONS, STYLE_OPTIONS, UNDERTONE_OPTIONS
from database import active_storage_backend, get_saved_outfits, init_db, save_outfit
from image_analysis import ImageAnalysisError, analyze_skin_from_upload
from knowledge_base import SOURCES
from recommendation_engine import generate_dress_suggestions, score_dress, generate_outfit_suggestions, get_avoid_colors, get_recommended_colors, score_breakdown
from session_manager import (
    current_user_id,
    current_username,
    initialize_session_state,
    is_authenticated,
    login_user,
    logout_user,
    start_guest_mode,
)
from llm_client import LLMUnavailableError, check_available as check_llm_available, load_config as load_llm_config
from style_assistant import build_grounded_answer, build_style_facts, stream_llm_answer
from supabase_auth_service import AuthenticationError, SupabaseAuthService, auth_is_available
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
    render_welcome_card,
    card,
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


def outfit_display_text(text: str, top: str, bottom: str) -> str:
    if top == "hoodie":
        text = text.replace("Shirt", "Hoodie").replace("shirt", "hoodie")
    if bottom == "skirt":
        text = text.replace("Pants", "Skirt").replace("pants", "skirt")
    return text


def normalize_skin_tone(value: str) -> str:
    if value == "very_fair":
        return "fair"
    if value == "deep_dark":
        return "dark"
    return value


def initialize_app_state() -> None:
    initialize_session_state()
    for key, default_value in DEFAULT_PROFILE.items():
        st.session_state.setdefault(key, default_value)

    st.session_state.setdefault("refinement_source", None)
    st.session_state.setdefault("avatar_model", "male")
    st.session_state.setdefault("female_shoe_style", "sneakers")
    st.session_state.setdefault("top_style", "shirt")
    st.session_state.setdefault("female_bottom_style", "skirt")
    st.session_state.setdefault("outerwear_color", "charcoal")


def save_current_outfit(
    skin_tone: str,
    undertone: str,
    style: str,
    occasion: str,
    shirt_color: str,
    pants_color: str,
    shoes_color: str,
    score: int,
    explanation: str | None = None,
) -> None:
    save_outfit(
        skin_tone=skin_tone,
        undertone=undertone,
        style=style,
        occasion=occasion,
        shirt_color=shirt_color,
        pants_color=pants_color,
        shoes_color=shoes_color,
        score=score,
        user_id=current_user_id(),
        username=current_username() if is_authenticated() else None,
        explanation=explanation,
        source="streamlit_local",
        metadata={"avatar_model": st.session_state.avatar_model,
                  "shoe_style": st.session_state.female_shoe_style if st.session_state.avatar_model == "female" else "sneakers",
                  "top_style": st.session_state.top_style,
                  "bottom_style": "dress" if st.session_state.top_style == "dress" else st.session_state.female_bottom_style if st.session_state.avatar_model == "female" else "pants",
                  "outerwear_color": st.session_state.outerwear_color},
    )


def load_outfit_into_builder(outfit: dict) -> None:
    """Runs as an on_click callback, i.e. before the builder widgets are instantiated."""
    st.session_state.builder_shirt_color = outfit["shirt_color"]
    st.session_state.builder_pants_color = outfit["pants_color"]
    st.session_state.builder_shoes_color = outfit["shoes_color"]
    st.session_state.refinement_source = outfit


st.set_page_config(
    page_title="StyleMatch AI",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "S",
    layout="wide",
)
inject_theme(LOGO_PATH if LOGO_PATH.exists() else None)

initialize_app_state()
init_db()
storage_backend = active_storage_backend()
auth_enabled, auth_message = auth_is_available()
auth_service = SupabaseAuthService() if auth_enabled else None

with st.sidebar:
    render_sidebar_brand(
        LOGO_PATH if LOGO_PATH.exists() else None,
        "StyleMatch AI",
        "Profile atelier controls",
    )
    st.caption("Set complexion, style, and occasion for a clean styling workflow.")

    render_sidebar_group_intro(
        "Access",
        "Sign in to keep saved looks per account, or continue locally as a guest.",
    )
    if auth_enabled:
        if is_authenticated():
            st.success(f"Signed in as {current_username()}")
            if st.button("Log out", width="stretch"):
                logout_user()
                st.rerun()
        else:
            access_mode = st.radio(
                "Session mode",
                options=["Guest", "Log in", "Sign up"],
                horizontal=True,
                label_visibility="collapsed",
            )
            if access_mode == "Guest":
                st.caption("Guest mode keeps styling local to this session.")
                if st.button("Continue as Guest", width="stretch"):
                    start_guest_mode(reset_state=True)
                    st.rerun()
            elif access_mode == "Log in":
                with st.form("login_form", clear_on_submit=False):
                    login_email = st.text_input("Email", key="login_email")
                    login_password = st.text_input("Password", type="password", key="login_password")
                    login_submit = st.form_submit_button("Log in", width="stretch")
                if login_submit:
                    try:
                        user = auth_service.authenticate_user(login_email, login_password) if auth_service else None
                    except AuthenticationError as exc:
                        st.error(str(exc))
                    else:
                        if user:
                            login_user(user)
                            st.rerun()
            else:
                with st.form("signup_form", clear_on_submit=False):
                    signup_display_name = st.text_input("Nickname", key="signup_display_name")
                    signup_email = st.text_input("Email", key="signup_email")
                    signup_password = st.text_input("Password", type="password", key="signup_password")
                    signup_confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
                    signup_submit = st.form_submit_button("Create account", width="stretch")
                if signup_submit:
                    if signup_password != signup_confirm:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            user = (
                                auth_service.register_user(signup_email, signup_password, signup_display_name)
                                if auth_service
                                else None
                            )
                        except AuthenticationError as exc:
                            st.error(str(exc))
                        else:
                            if user:
                                login_user(user)
                                st.rerun()
    else:
        start_guest_mode(reset_state=False)
        st.caption("Supabase auth is not configured yet.")
        if auth_message:
            st.caption(auth_message)

    render_sidebar_group_intro("Avatar", "Choose the body model for your outfit previews.")
    st.selectbox("Avatar model", ["male", "female"], key="avatar_model",
                 format_func=lambda value: "Man" if value == "male" else "Woman")
    if st.session_state.avatar_model == "male" and st.session_state.top_style == "dress":
        st.session_state.top_style = "shirt"
    top_options = ["shirt", "hoodie", "jacket", "dress"] if st.session_state.avatar_model == "female" else ["shirt", "hoodie", "jacket"]
    st.selectbox("Top / outfit", top_options, key="top_style", format_func=str.title)
    if st.session_state.top_style == "jacket":
        st.selectbox("Jacket color", ALL_COLORS, key="outerwear_color", format_func=humanize_value)
    if st.session_state.avatar_model == "female":
        if st.session_state.top_style != "dress":
            st.selectbox("Bottom", ["skirt", "pants"], key="female_bottom_style", format_func=str.title)
        st.selectbox("Footwear", ["sneakers", "heels"], key="female_shoe_style",
                     format_func=str.title)
        st.caption("Choose Dress for a one-piece look, or a top with a skirt or pants.")

    render_sidebar_group_intro(
        "Complexion",
        "Choose a tone and undertone to anchor the styling direction.",
    )
    st.session_state.skin_tone = render_skin_tone_picker(UI_SKIN_TONE_OPTIONS, "skin_tone")
    st.session_state.undertone = render_icon_choice_group(
        UNDERTONE_OPTIONS,
        "undertone",
        UNDERTONE_META,
        columns_per_row=1,
    )

    render_sidebar_group_intro(
        "Wardrobe Direction",
        "Choose the aesthetic and setting to refine the recommendations.",
    )
    st.session_state.style = render_icon_choice_group(STYLE_OPTIONS, "style", STYLE_META, columns_per_row=2)
    st.session_state.occasion = render_icon_choice_group(
        OCCASION_OPTIONS,
        "occasion",
        OCCASION_META,
        columns_per_row=2,
    )

avatar_model = st.session_state.avatar_model
bottom_style = st.session_state.female_bottom_style if avatar_model == "female" else "pants"
top_style = st.session_state.top_style
if top_style == "dress":
    bottom_style = "dress"
bottom_label = "Skirt" if bottom_style == "skirt" else "Pants"
top_label = "Dress" if top_style == "dress" else "Hoodie" if top_style == "hoodie" else "Shirt"
skin_tone = normalize_skin_tone(st.session_state.skin_tone)
undertone = st.session_state.undertone
style = st.session_state.style
occasion = st.session_state.occasion

recommended_colors = get_recommended_colors(undertone, style, occasion)
avoid_colors = get_avoid_colors(undertone)

render_branded_header(
    LOGO_PATH if LOGO_PATH.exists() else None,
    "StyleMatch AI",
    "Build outfits around your complexion and occasion.",
)
if auth_enabled and is_authenticated():
    render_welcome_card(current_username())
render_profile_band(
    {
        "Skin Tone": skin_tone,
        "Undertone": undertone,
        "Style": style,
        "Occasion": occasion,
    }
)
if storage_backend == "supabase":
    if is_authenticated():
        render_note_chip("Supabase sync is active for your saved looks.")
    else:
        render_note_chip("Supabase sync is configured. Sign in to keep looks under your own account.")
else:
    render_note_chip("Local mode is active. Saved looks stay on this device.")

tab_analyzer, tab_builder, tab_generator, tab_assistant, tab_saved, tab_sources = st.tabs(
    ["Image Analyzer", "Outfit Builder", "Generate 5 Looks", "AI Style Assistant", "Saved Looks", "Sources"]
)

with tab_analyzer:
    render_section_intro(
        "Image Atelier",
        "Profile your complexion with a polished upload workflow",
        "Drop in a well-lit portrait to estimate skin tone and undertone, then carry that profile straight into the recommendation engine.",
    )
    with card():
        render_panel_heading(
            "Upload Studio",
            "Analyze a front-facing portrait",
            "Use natural lighting and a clear frontal angle for the most grounded result.",
        )
        uploaded_file = st.file_uploader("Upload a clear front-facing image", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            with st.spinner("Analyzing your portrait…"):
                result = analyze_skin_from_upload(uploaded_file)
        except ImageAnalysisError as exc:
            st.error(str(exc))
        except Exception:
            st.error("The image could not be analyzed. Please try a different photo.")
        else:
            info_col, image_col = st.columns([1, 1], gap="large")

            with info_col:
                with card():
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

                    if st.button("Use detected profile", key="use_detected_profile", type="primary"):
                        st.session_state.skin_tone = normalize_skin_tone(str(result["skin_tone"]))
                        st.session_state.undertone = str(result["undertone"])
                        st.rerun()

            with image_col:
                with card():
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
        "Choose dress and shoe colors for a complete one-piece look." if top_style == "dress" else f"Dial in {top_label.lower()}, {bottom_label.lower()}, and shoes while the engine explains why the palette works with your undertone and context.",
    )
    left_col, right_col = st.columns([1.06, 0.94], gap="large")

    with left_col:
        with card():
            render_panel_heading(
                "Curate",
                "Design your outfit combination",
                "Start with recommended tones, then push the palette toward a more editorial direction if you want to experiment.",
            )
            if st.session_state.refinement_source:
                render_note_chip("Refining a generated look. Saving will add it to your local archive.")
            shirt_options = recommended_colors + [color for color in ALL_COLORS if color not in recommended_colors]
            shirt_color = render_color_select(f"{top_label} Color", shirt_options, shirt_options[0], "builder_shirt_color", COLOR_MAP)
            pants_color = shirt_color if top_style == "dress" else render_color_select(f"{bottom_label} Color", ALL_COLORS, "black", "builder_pants_color", COLOR_MAP)
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

            if top_style == "dress":
                score, reasons = score_dress(skin_tone, undertone, style, occasion, shirt_color, shoes_color)

            render_score_badge(score)
            render_color_legend("Recommended palette", recommended_colors, color_map=COLOR_MAP)
            render_color_legend("Lower-priority colors", avoid_colors, muted=True, color_map=COLOR_MAP)

            st.markdown("#### Why this score?")
            for reason in reasons:
                st.write(f"- {outfit_display_text(reason, top_style, bottom_style)}")

            if st.button("Save this outfit", type="primary", width="stretch"):
                save_current_outfit(
                    skin_tone=skin_tone,
                    undertone=undertone,
                    style=style,
                    occasion=occasion,
                    shirt_color=shirt_color,
                    pants_color=pants_color,
                    shoes_color=shoes_color,
                    score=score,
                )
                st.session_state.refinement_source = None
                if storage_backend == "supabase" and is_authenticated():
                    st.success("Outfit saved to Supabase.")
                else:
                    st.success("Outfit saved locally.")

    with right_col:
        with card():
            render_panel_heading(
                "Avatar Preview",
                "See the silhouette in context",
                "A premium preview card for checking balance, contrast, and how the pieces land together visually.",
            )
            avatar = render_avatar(
                avatar_model=avatar_model,
                shoe_style=st.session_state.female_shoe_style,
                top_style=top_style,
                bottom_style=bottom_style,
                outerwear_color=st.session_state.outerwear_color,
                skin_tone=skin_tone,
                shirt_color=shirt_color,
                pants_color=pants_color,
                shoes_color=shoes_color,
            )
            st.image(avatar, width="content")
            st.markdown(
                '<div class="avatar-caption">Rendered from layered fashion assets tinted to your current outfit selection.</div>',
                unsafe_allow_html=True,
            )

with tab_generator:
    render_section_intro(
        "Look Generator",
        "Generate fast, premium-ready outfit directions",
        "Explore automatically composed looks ranked by harmony, versatility, and contrast so you can shortlist ideas quickly.",
    )
    suggestions = (generate_dress_suggestions if top_style == "dress" else generate_outfit_suggestions)(
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
            with card("look"):
                render_panel_heading(
                    "Featured Avatar",
                    "Top-ranked generated look",
                    "Preview the strongest combination first, then compare the full set of five recommendations beside it.",
                )
                featured_avatar = render_avatar(
                    avatar_model=avatar_model,
                    shoe_style=st.session_state.female_shoe_style,
                    top_style=top_style,
                    bottom_style=bottom_style,
                    outerwear_color=st.session_state.outerwear_color,
                    skin_tone=skin_tone,
                    shirt_color=featured["shirt_color"],
                    pants_color=featured["pants_color"],
                    shoes_color=featured["shoes_color"],
                    width=330,
                    height=500,
                )
                st.image(featured_avatar, width="content")
                render_score_badge(featured["score"])
                st.caption(outfit_display_text(featured["explanation"], top_style, bottom_style))

        with summary_col:
            for idx, outfit in enumerate(suggestions, start=1):
                with card("look"):
                    render_panel_heading(
                        f"Look {idx}",
                        f"{humanize_value(outfit['shirt_color'])}, {humanize_value(outfit['pants_color'])}, {humanize_value(outfit['shoes_color'])}",
                        f"{humanize_value(outfit['harmony'])} harmony with a {outfit['score']}/100 match score.",
                    )
                    st.write(f"**{top_label}:** {humanize_value(outfit['shirt_color'])}")
                    if top_style != "dress":
                        st.write(f"**{bottom_label}:** {humanize_value(outfit['pants_color'])}")
                    st.write(f"**Shoes:** {humanize_value(outfit['shoes_color'])}")
                    st.caption(outfit_display_text(outfit["explanation"], top_style, bottom_style))
                    for reason in outfit.get("reasons", [])[:2]:
                        st.write(f"- {outfit_display_text(reason, top_style, bottom_style)}")

                    refine_col, save_col = st.columns(2, gap="small")
                    with refine_col:
                        st.button(
                            "Refine in Builder",
                            key=f"refine_generated_{idx}",
                            width="stretch",
                            on_click=load_outfit_into_builder,
                            args=(outfit,),
                        )
                    with save_col:
                        if st.button(f"Save Look {idx}", key=f"save_generated_{idx}", type="primary", width="stretch"):
                            save_current_outfit(
                                skin_tone=skin_tone,
                                undertone=undertone,
                                style=style,
                                occasion=occasion,
                                shirt_color=outfit["shirt_color"],
                                pants_color=outfit["pants_color"],
                                shoes_color=outfit["shoes_color"],
                                score=outfit["score"],
                                explanation=outfit["explanation"],
                            )
                            if storage_backend == "supabase" and is_authenticated():
                                st.success(f"Look {idx} saved to Supabase.")
                            else:
                                st.success(f"Look {idx} saved locally.")

with tab_assistant:
    render_section_intro(
        "AI Concierge",
        "Ask your stylist",
        "Answers use your profile, the colour rules, and the engine's score for the outfit in the Builder.",
    )
    llm_config = load_llm_config()
    llm_ready, llm_status = check_llm_available(llm_config)
    with card():
        render_panel_heading(
            "Prompt",
            "What are you dressing for?",
            "Ask in English or Hebrew. The assistant only uses verified style facts and never invents a score.",
        )
        render_note_chip(("● " if llm_ready else "○ ") + (llm_status if llm_ready else f"Rule-based mode · {llm_status}"))
        question = st.text_area(
            "Your question",
            placeholder="What should I wear for a date tonight? / מה ללבוש לראיון עבודה?",
            height=110,
        )
        include_builder = st.checkbox("Include the outfit from the Builder", value=True)
        ask = st.button("Ask the stylist", key="ask_assistant", type="primary")

    if ask:
        facts = build_style_facts(
            skin_tone=skin_tone,
            undertone=undertone,
            style=style,
            occasion=occasion,
            top_label=top_label,
            bottom_label=bottom_label,
            is_dress=top_style == "dress",
            current_outfit=(
                {
                    "shirt_color": shirt_color,
                    "pants_color": pants_color,
                    "shoes_color": shoes_color,
                    "score": score,
                    "reasons": [outfit_display_text(r, top_style, bottom_style) for r in reasons],
                }
                if include_builder
                else None
            ),
        )
        st.session_state.assistant_question = question
        st.session_state.assistant_answer = None
        with card("answer"):
            render_panel_heading("Stylist", "Your answer", "")
            if llm_ready:
                try:
                    with st.spinner("Thinking about your look…" if not llm_config.is_local else "Thinking… a local model can take up to a minute."):
                        stream = stream_llm_answer(question, facts)
                        first = next(stream, "")
                    answer_text = st.write_stream(itertools.chain([first], stream))
                    st.session_state.assistant_answer = (answer_text, llm_config.label)
                    st.caption(f"Generated by {llm_config.label} from StyleMatch facts. Scores come from the scoring engine.")
                except LLMUnavailableError as exc:
                    st.warning(f"The LLM did not answer ({exc}). Showing rule-based guidance instead.")
                    llm_ready = False
            if not llm_ready:
                fallback = build_grounded_answer(
                    skin_tone=skin_tone,
                    undertone=undertone,
                    style=style,
                    occasion=occasion,
                    user_prompt=question,
                )
                st.text(fallback)
                st.session_state.assistant_answer = (fallback, "rule-based")
        with st.expander("Facts the stylist used"):
            st.text(facts)
    elif st.session_state.get("assistant_answer"):
        answer_text, answer_source = st.session_state.assistant_answer
        with card("answer"):
            render_panel_heading("Stylist", "Last answer", st.session_state.get("assistant_question", ""))
            if answer_source == "rule-based":
                st.text(answer_text)
            else:
                st.markdown(answer_text)
            st.caption(f"Source: {answer_source}")

with tab_saved:
    render_section_intro(
        "Saved Looks",
        "Review your archived outfit decisions",
        "A running wardrobe history of combinations you chose to keep, complete with profile context and avatar previews.",
    )
    saved_outfits = get_saved_outfits(current_user_id())

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
                        "Stored for later review so you can revisit combinations that felt right.",
                    )
                    if outfit.get("username"):
                        st.write(f"**Account:** {outfit['username']}")
                    st.write(f"**Skin tone:** {humanize_value(outfit['skin_tone'])}")
                    st.write(f"**Undertone:** {humanize_value(outfit['undertone'])}")
                    st.write(f"**Style:** {humanize_value(outfit['style'])}")
                    st.write(f"**Occasion:** {humanize_value(outfit['occasion'])}")
                    saved_top = outfit.get("metadata", {}).get("top_style", "shirt")
                    st.write(f"**Top:** {saved_top.title()}")
                    st.write(f"**{'Dress' if saved_top == 'dress' else 'Hoodie' if saved_top == 'hoodie' else 'Shirt'}:** {humanize_value(outfit['shirt_color'])}")
                    if saved_top == "jacket":
                        st.write(f"**Jacket:** {humanize_value(outfit.get('metadata', {}).get('outerwear_color', 'charcoal'))}")
                    if saved_top != "dress":
                        st.write(f"**{'Skirt' if outfit.get('metadata', {}).get('bottom_style', 'skirt' if outfit.get('metadata', {}).get('avatar_model') == 'female' else 'pants') == 'skirt' else 'Pants'}:** {humanize_value(outfit['pants_color'])}")
                    st.write(f"**Shoes:** {humanize_value(outfit['shoes_color'])}")
                    st.caption(f"Saved at: {outfit['created_at']}")

                with preview_col:
                    saved_avatar = render_avatar(
                        avatar_model=outfit.get("metadata", {}).get("avatar_model", "male"),
                        shoe_style=outfit.get("metadata", {}).get("shoe_style", "sneakers"),
                        top_style=outfit.get("metadata", {}).get("top_style", "shirt"),
                        bottom_style=outfit.get("metadata", {}).get("bottom_style"),
                        outerwear_color=outfit.get("metadata", {}).get("outerwear_color", "charcoal"),
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
        with card():
            render_panel_heading(
                "Embedded Source",
                source["title"],
                source["summary"],
            )
            st.code(source["url"], language="text")

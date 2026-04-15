from __future__ import annotations

import streamlit as st


def render_color_legend(title: str, colors: list[str]) -> None:
    st.markdown(f"#### {title}")
    if not colors:
        st.caption("No items to show.")
        return

    chips = []
    for color in colors:
        chips.append(
            f'''
            <div style="
                display:inline-block;
                padding:8px 12px;
                margin:4px;
                border-radius:999px;
                border:1px solid #d1d5db;
                background:#ffffff;
                font-size:14px;">
                {color}
            </div>
            '''
        )
    st.markdown("".join(chips), unsafe_allow_html=True)


def render_score_badge(score: int) -> None:
    if score >= 85:
        label = "Excellent match"
    elif score >= 70:
        label = "Good match"
    elif score >= 55:
        label = "Safe match"
    else:
        label = "Needs improvement"
    st.metric("Outfit Match Score", f"{score}/100", label)

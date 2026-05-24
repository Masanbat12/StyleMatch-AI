from __future__ import annotations

from uuid import uuid4

import streamlit as st


SESSION_DEFAULTS = {
    "auth_mode": "guest",
    "current_user": None,
    "guest_context": None,
    "guest_saved_looks": None,
    "guest_skin_history": None,
    "guest_feedback_history": None,
    "guest_session_id": None,
    "auth_message": None,
}


def initialize_session_state() -> None:
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)

    if st.session_state.guest_session_id is None:
        st.session_state.guest_session_id = f"guest-{uuid4().hex[:12]}"
    if st.session_state.guest_context is None:
        st.session_state.guest_context = {}
    if st.session_state.guest_saved_looks is None:
        st.session_state.guest_saved_looks = []
    if st.session_state.guest_skin_history is None:
        st.session_state.guest_skin_history = []
    if st.session_state.guest_feedback_history is None:
        st.session_state.guest_feedback_history = []


def reset_guest_state() -> None:
    st.session_state.guest_session_id = f"guest-{uuid4().hex[:12]}"
    st.session_state.guest_context = {}
    st.session_state.guest_saved_looks = []
    st.session_state.guest_skin_history = []
    st.session_state.guest_feedback_history = []


def start_guest_mode(reset_state: bool = False) -> None:
    if reset_state:
        reset_guest_state()
    st.session_state.auth_mode = "guest"
    st.session_state.current_user = None
    st.session_state.auth_message = "Guest mode is active. Preferences are temporary for this session only."


def login_user(user: dict) -> None:
    st.session_state.auth_mode = "authenticated"
    st.session_state.current_user = {
        "id": user["id"],
        "username": user["username"],
    }
    st.session_state.auth_message = f"Signed in as {user['username']}."


def logout_user() -> None:
    start_guest_mode(reset_state=True)


def is_authenticated() -> bool:
    return st.session_state.auth_mode == "authenticated" and bool(st.session_state.current_user)


def is_guest_mode() -> bool:
    return st.session_state.auth_mode == "guest"


def current_user_id() -> str:
    if is_authenticated():
        return str(st.session_state.current_user["id"])
    return str(st.session_state.guest_session_id)


def current_username() -> str:
    if is_authenticated():
        return str(st.session_state.current_user["username"])
    return "Guest"

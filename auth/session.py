"""Session state helpers — single source of truth for auth state."""
from __future__ import annotations

import streamlit as st


def init_session() -> None:
    defaults = {
        "authenticated": False,
        "user_id": None,
        "user_email": None,
        "user_name": None,
        "page": "login",
        "pending_email": None,   # email awaiting OTP verification
        "otp_purpose": None,     # "register" | "reset_password"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def login(user_id: str, email: str, name: str = "") -> None:
    st.session_state.authenticated = True
    st.session_state.user_id = user_id
    st.session_state.user_email = email
    st.session_state.user_name = name
    st.session_state.page = "dashboard"


def logout() -> None:
    for key in ["authenticated", "user_id", "user_email", "user_name"]:
        st.session_state[key] = None if key != "authenticated" else False
    st.session_state.page = "login"


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def current_user_id() -> str | None:
    return st.session_state.get("user_id")


def current_email() -> str | None:
    return st.session_state.get("user_email")


def current_name() -> str | None:
    return st.session_state.get("user_name")

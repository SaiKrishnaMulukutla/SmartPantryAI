"""Login page."""
from __future__ import annotations

import streamlit as st

from auth.password import verify_password
from auth.session import go, login
from db.users import get_user_by_email


def render() -> None:
    st.markdown("""
    <div class="auth-card">
      <h2>Welcome back 👋</h2>
      <p class="subtitle">Sign in to SmartPantryAI</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email address", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("Sign In", type="primary", use_container_width=True)
        col2.form_submit_button("Forgot password?", use_container_width=True,
                                on_click=lambda: go("forgot_password"))

    if submit:
        if not email or not password:
            st.error("Please enter your email and password.")
            return

        user = get_user_by_email(email.strip().lower())
        if not user:
            st.error("No account found with that email.")
            return
        if not user["is_verified"]:
            st.warning("Please verify your email first. Check your inbox.")
            st.session_state.pending_email = email.strip().lower()
            st.session_state.otp_purpose = "register"
            go("verify_otp")
            return
        if not verify_password(password, user["password_hash"]):
            st.error("Incorrect password.")
            return

        login(user["id"], user["email"])
        st.rerun()

    st.markdown("<hr class='section-divider'/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Create an account", use_container_width=True):
            go("register")

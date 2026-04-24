"""Login page."""
from __future__ import annotations

import streamlit as st

from auth.password import verify_password
from auth.session import go, login
from db.users import get_user_by_email


_AUTH_LAYOUT_CSS = """
<style>
[data-testid="stMain"] .block-container {
  max-width: 520px !important;
  padding-top: 60px !important;
}
</style>
"""


def render() -> None:
    st.markdown(_AUTH_LAYOUT_CSS, unsafe_allow_html=True)
    # Handle forgot-password link navigation (query param set by HTML anchor below)
    if st.query_params.get("_nav") == "forgot":
        st.query_params.clear()
        go("forgot_password")
        return

    with st.form("login_form"):
        st.markdown("""
        <div class="auth-heading">
            <h2>Welcome to SmartPantryAI</h2>
            <p>Sign in to your account</p>
        </div>
        """, unsafe_allow_html=True)

        email    = st.text_input("Email address", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit   = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    # Forgot password — real HTML link, centred below the form card
    st.markdown("""
    <div style="text-align:center; margin-top:12px;">
      <a href="?_nav=forgot"
         style="color:#2563EB; font-size:13px; text-decoration:none;">
        Forgot password?
      </a>
    </div>
    """, unsafe_allow_html=True)

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
            st.session_state.otp_purpose   = "register"
            go("verify_otp")
            return
        if not verify_password(password, user["password_hash"]):
            st.error("Incorrect password.")
            return

        login(user["id"], user["email"], user.get("name", ""))
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Create an account", use_container_width=True):
            go("register")

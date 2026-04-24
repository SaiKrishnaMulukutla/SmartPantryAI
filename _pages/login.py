"""Login page."""
from __future__ import annotations

import streamlit as st

from auth.otp import send_otp
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

    st.markdown("""
    <div class="auth-heading">
        <h2>Welcome to SmartPantryAI</h2>
        <p>Sign in to your account</p>
    </div>
    """, unsafe_allow_html=True)

    tab_pwd, tab_otp = st.tabs(["Password", "Email OTP"])

    # ── Tab 1: Password login ────────────────────────────────────────────
    with tab_pwd:
        with st.form("login_password_form"):
            email_pwd = st.text_input("Email address", placeholder="Enter your email",
                                      key="pwd_email")
            password  = st.text_input("Password", type="password",
                                      placeholder="Enter your password", key="pwd_pass")
            submit_pwd = st.form_submit_button("Sign In", type="primary",
                                               use_container_width=True)

        st.markdown("""
        <div style="text-align:center; margin-top:8px;">
          <a href="?_nav=forgot" style="color:#2563EB; font-size:13px; text-decoration:none;">
            Forgot password?
          </a>
        </div>
        """, unsafe_allow_html=True)

        if submit_pwd:
            if not email_pwd or not password:
                st.error("Please enter your email and password.")
                return
            user = get_user_by_email(email_pwd.strip().lower())
            if not user:
                st.error("No account found with that email.")
                return
            if not user["is_verified"]:
                st.warning("Please verify your email first.")
                st.session_state.pending_email = email_pwd.strip().lower()
                st.session_state.otp_purpose   = "register"
                go("verify_otp")
                return
            if not verify_password(password, user["password_hash"]):
                st.error("Incorrect password.")
                return
            login(user["id"], user["email"], user.get("name", ""))
            st.rerun()

    # ── Tab 2: Email OTP login ───────────────────────────────────────────
    with tab_otp:
        with st.form("login_otp_form"):
            email_otp  = st.text_input("Email address", placeholder="Enter your email",
                                       key="otp_email")
            submit_otp = st.form_submit_button("Send OTP", type="primary",
                                               use_container_width=True)

        if submit_otp:
            if not email_otp:
                st.error("Please enter your email.")
                return
            user = get_user_by_email(email_otp.strip().lower())
            if not user:
                st.error("No account found with that email.")
                return
            if not user["is_verified"]:
                st.warning("Please verify your email first.")
                st.session_state.pending_email = email_otp.strip().lower()
                st.session_state.otp_purpose   = "register"
                go("verify_otp")
                return
            with st.spinner("Sending OTP…"):
                send_otp(email_otp.strip().lower(), purpose="login_otp")
            st.session_state.pending_email = email_otp.strip().lower()
            st.session_state.otp_purpose   = "login_otp"
            go("verify_otp")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Create an account", use_container_width=True):
            go("register")

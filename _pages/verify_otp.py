"""OTP verification page — used for registration and password reset."""
from __future__ import annotations

import streamlit as st

from auth.email.sender import send_email
from auth.otp import send_otp, verify
from auth.session import go, login
from db.users import get_user_by_email, mark_verified, update_password
from auth.password import hash_password


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
    email = st.session_state.get("pending_email", "")
    purpose = st.session_state.get("otp_purpose", "register")

    if not email:
        go("login")
        return

    titles = {
        "register":       "Verify your email",
        "reset_password": "Reset your password",
        "login_otp":      "Sign in with OTP",
    }
    title = titles.get(purpose, "Verify your email")

    with st.form("otp_form"):
        st.markdown(f"""
        <div class="auth-heading">
            <h2>{title}</h2>
            <p>We sent a 6-digit code to <strong>{email}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        otp = st.text_input("Enter 6-digit code", placeholder="_ _ _ _ _ _",
                            max_chars=6)

        if purpose == "reset_password":
            new_password = st.text_input("New password", type="password", placeholder="Min. 8 characters")
            confirm = st.text_input("Confirm new password", type="password")
        else:
            new_password = confirm = None

        submit = st.form_submit_button("Verify", type="primary", use_container_width=True)

    if submit:
        if len(otp.strip()) != 6:
            st.error("Enter a valid 6-digit code.")
            return

        if not verify(email, otp):
            st.error("Invalid or expired code. Request a new one below.")
            return

        if purpose == "register":
            mark_verified(email)
            user = get_user_by_email(email)
            send_email(email, template="welcome", context={"email": email})
            login(user["id"], user["email"], user.get("name", ""))
            st.success("Email verified! Welcome to SmartPantryAI 🎉")
            st.rerun()

        elif purpose == "login_otp":
            user = get_user_by_email(email)
            login(user["id"], user["email"], user.get("name", ""))
            st.rerun()

        elif purpose == "reset_password":
            if not new_password or len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
                return
            if new_password != confirm:
                st.error("Passwords do not match.")
                return
            update_password(email, hash_password(new_password))
            st.success("Password reset! You can now sign in.")
            go("login")

    st.markdown("<hr class='section-divider'/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Resend code", use_container_width=True):
            with st.spinner("Sending…"):
                send_otp(email, purpose=purpose)
            st.success("New code sent! Check your inbox.")

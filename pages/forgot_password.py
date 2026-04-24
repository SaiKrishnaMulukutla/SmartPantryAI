"""Forgot password — sends reset OTP."""
from __future__ import annotations

import streamlit as st

from auth.otp import send_otp
from auth.session import go
from db.users import get_user_by_email


def render() -> None:
    st.markdown("""
    <div class="auth-card">
      <h2>Forgot password?</h2>
      <p class="subtitle">Enter your email and we'll send a reset code</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("forgot_form"):
        email = st.text_input("Email address", placeholder="you@example.com")
        submit = st.form_submit_button("Send Reset Code", type="primary", use_container_width=True)

    if submit:
        email = email.strip().lower()
        user = get_user_by_email(email)
        if not user:
            # Don't reveal if email exists — security best practice
            st.success("If that email is registered, a reset code has been sent.")
        else:
            with st.spinner("Sending reset code…"):
                send_otp(email, purpose="reset_password")
            st.session_state.pending_email = email
            st.session_state.otp_purpose = "reset_password"
            st.success("Reset code sent! Check your inbox.")
            go("verify_otp")

    st.markdown("<hr class='section-divider'/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Back to Sign In", use_container_width=True):
            go("login")

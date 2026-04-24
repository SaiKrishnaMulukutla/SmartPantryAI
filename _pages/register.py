"""Registration page."""
from __future__ import annotations

import re
import streamlit as st

from auth.otp import send_otp
from auth.password import hash_password
from auth.session import go
from db.users import create_user, email_exists


_EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[a-z]{2,}$", re.I)


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
    with st.form("register_form"):
        st.markdown("""
        <div class="auth-heading">
            <h2>Create account</h2>
            <p>Join SmartPantryAI — it's free</p>
        </div>
        """, unsafe_allow_html=True)
        name     = st.text_input("Full name", placeholder="Your name")
        email    = st.text_input("Email address", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Min. 8 characters")
        confirm  = st.text_input("Confirm password", type="password", placeholder="Re-enter password")
        submit   = st.form_submit_button("Create Account", type="primary", use_container_width=True)

    if submit:
        name  = name.strip()
        email = email.strip().lower()

        if not name:
            st.error("Please enter your name.")
            return
        if not _EMAIL_RE.match(email):
            st.error("Enter a valid email address.")
            return
        if len(password) < 8:
            st.error("Password must be at least 8 characters.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        if email_exists(email):
            st.warning("An account with this email already exists.")
            if st.button("Sign in instead"):
                go("login")
            return

        with st.spinner("Creating your account…"):
            create_user(email, hash_password(password), name)
            send_otp(email, purpose="register")

        st.session_state.pending_email = email
        st.session_state.pending_name  = name
        st.session_state.otp_purpose = "register"
        go("verify_otp")

    st.markdown("<hr class='section-divider'/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Already have an account? Sign in", use_container_width=True):
            go("login")

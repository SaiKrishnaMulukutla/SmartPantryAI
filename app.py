"""SmartPantryAI — entry point and router."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="SmartPantryAI",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject design tokens ─────────────────────────────────────────────
from ui.theme import inject as _inject_theme
_inject_theme()

_CSS_PATH = Path(__file__).parent / "ui" / "styles.css"
if _CSS_PATH.exists():
    st.markdown(f"<style>{_CSS_PATH.read_text()}</style>", unsafe_allow_html=True)

# ── Session init ─────────────────────────────────────────────────────
from auth.session import init_session, is_authenticated, logout, go
init_session()

# ── Sidebar nav (authenticated only) ────────────────────────────────
if is_authenticated():
    from auth.session import current_email
    with st.sidebar:
        st.markdown(f"👤 **{current_email()}**")
        st.markdown("---")
        if st.button("🏠 Dashboard", use_container_width=True):
            go("dashboard")
        if st.button("📖 History", use_container_width=True):
            go("history")
        if st.button("❤️ Favourites", use_container_width=True):
            go("favourites")
        st.markdown("---")
        if st.button("Sign Out", use_container_width=True):
            logout()
            st.rerun()

# ── Router ───────────────────────────────────────────────────────────
page = st.session_state.get("page", "login")

if not is_authenticated():
    if page == "register":
        from pages.register import render
    elif page == "verify_otp":
        from pages.verify_otp import render
    elif page == "forgot_password":
        from pages.forgot_password import render
    else:
        from pages.login import render
else:
    if page == "history":
        from pages.history import render
    elif page == "favourites":
        from pages.favourites import render
    else:
        from pages.dashboard import render

render()

"""SmartPantryAI — entry point and router."""
from __future__ import annotations

from pathlib import Path

import truststore
truststore.inject_into_ssl()  # must be before any ssl/httpx/smtplib usage

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
    from auth.session import current_email, current_name
    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="sidebar-brand">
            <span class="sidebar-brand-icon">🍳</span>
            <span class="sidebar-brand-name">SmartPantryAI</span>
        </div>
        """, unsafe_allow_html=True)

        # Profile card — show name, fall back to email
        name  = current_name() or ""
        email = current_email() or ""
        display = name if name else email
        initials = display[0].upper() if display else "U"
        st.markdown(f"""
        <div class="sidebar-profile">
            <div class="sidebar-avatar">{initials}</div>
            <div class="sidebar-user-email">{display}</div>
        </div>
        """, unsafe_allow_html=True)

        # Active-state highlight: inject a rule targeting the current page's button
        _page = st.session_state.get("page", "dashboard")
        _pos  = {"dashboard": 1, "history": 2, "favourites": 3}.get(_page, 1)
        st.markdown(f"""
        <style>
        [data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type({_pos}) > button {{
            background: var(--green-bg) !important;
            color: var(--green) !important;
            font-weight: 600 !important;
            border-left: 3px solid var(--green) !important;
        }}
        </style>
        """, unsafe_allow_html=True)

        # Nav
        if st.button("🏠  Dashboard", use_container_width=True, key="nav_dashboard"):
            go("dashboard")
        if st.button("📖  History", use_container_width=True, key="nav_history"):
            go("history")
        if st.button("❤️  Favourites", use_container_width=True, key="nav_favourites"):
            go("favourites")

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("---")

        # Sign out — muted styling via 4th button position
        st.markdown("""
        <style>
        [data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(4) > button {
            color: var(--muted) !important;
            font-size: 13px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True, key="nav_signout"):
            logout()
            st.rerun()

# ── Router ───────────────────────────────────────────────────────────
page = st.session_state.get("page", "login")

if not is_authenticated():
    if page == "register":
        from _pages.register import render
    elif page == "verify_otp":
        from _pages.verify_otp import render
    elif page == "forgot_password":
        from _pages.forgot_password import render
    else:
        from _pages.login import render
else:
    if page == "history":
        from _pages.history import render
    elif page == "favourites":
        from _pages.favourites import render
    else:
        from _pages.dashboard import render

render()

"""Inject global CSS design tokens into Streamlit."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
/* ── Tokens ─────────────────────────────────────────── */
:root {
  --green:      #2D6A4F;
  --green-lt:   #52B788;
  --green-bg:   #F0FFF7;
  --amber:      #F4A261;
  --amber-bg:   #FFF7F0;
  --bg:         #FAFAF8;
  --card-bg:    #FFFFFF;
  --border:     #E8EAE5;
  --text:       #1A1A1A;
  --muted:      #6B7280;
  --radius:     10px;
  --shadow:     0 2px 16px rgba(0,0,0,0.08);
}

/* ── Global ─────────────────────────────────────────── */
html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container {
  background: var(--bg) !important;
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: #F6F8F5 !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 24px !important;
}

/* Brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 4px 20px;
}
.sidebar-brand-icon { font-size: 26px; line-height: 1; }
.sidebar-brand-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--green);
  letter-spacing: -0.3px;
}

/* Profile card */
.sidebar-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}
.sidebar-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--green);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}
.sidebar-user-email {
  font-size: 12px;
  color: var(--muted);
  word-break: break-all;
  line-height: 1.4;
}

/* Nav buttons */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  background: transparent !important;
  color: var(--text) !important;
  border: none !important;
  border-radius: 8px !important;
  text-align: left !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  padding: 10px 14px !important;
  transition: background 0.15s, color 0.15s !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
  background: var(--green-bg) !important;
  color: var(--green) !important;
}

/* ══════════════════════════════════════════════════════
   AUTH PAGES
══════════════════════════════════════════════════════ */

/* Style the form as the card */
[data-testid="stForm"] {
  background: var(--card-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 36px 40px !important;
  box-shadow: var(--shadow) !important;
}

/* Auth heading inside the form */
.auth-heading h2 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text) !important;
}
.auth-heading p {
  margin: 0 0 24px;
  font-size: 14px;
  color: var(--muted);
}

/* OTP box */
.otp-display {
  background: var(--green-bg);
  border: 2px dashed var(--green);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
  font-size: 36px;
  font-weight: 800;
  letter-spacing: 10px;
  color: var(--green);
  font-family: 'Courier New', monospace;
  margin: 16px 0;
}

/* ══════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════ */

/* Primary */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: var(--green) !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  letter-spacing: 0.2px !important;
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  background: #235c42 !important;
  box-shadow: 0 4px 12px rgba(45,106,79,0.3) !important;
}

/* Secondary — outlined green */
[data-testid="stBaseButton-secondary"] {
  background: var(--green-bg) !important;
  border: 1.5px solid var(--green-lt) !important;
  border-radius: 8px !important;
  color: var(--green) !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[data-testid="stBaseButton-secondary"]:hover {
  background: #d8f3e8 !important;
  border-color: var(--green) !important;
}

/* ══════════════════════════════════════════════════════
   INPUTS
══════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input {
  background: #ffffff !important;
  border: 1.5px solid #C8D5CB !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  padding: 10px 14px !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--green) !important;
  box-shadow: 0 0 0 3px rgba(45,106,79,0.12) !important;
  background: #ffffff !important;
}
[data-testid="stTextInput"] input::placeholder {
  color: #A0ADA4 !important;
}

/* ══════════════════════════════════════════════════════
   RECIPE CARDS
══════════════════════════════════════════════════════ */

div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  background: var(--card-bg) !important;
  margin-bottom: 12px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div > div {
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

/* Card header */
.rc-name {
  font-size: 19px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 10px;
  line-height: 1.3;
}

/* Cuisine / time badges */
.rc-badge {
  display: inline-block;
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 500;
  margin-right: 6px;
}
.rc-badge-green {
  background: var(--green-bg);
  color: var(--green);
  border: 1px solid var(--green-lt);
}
.rc-badge-amber {
  background: var(--amber-bg);
  color: #B85C2A;
  border: 1px solid var(--amber);
}

/* Section label */
.rc-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--muted);
  margin: 0 0 10px;
}

/* Ingredient lines */
.ing-item {
  font-size: 13px;
  color: var(--text);
  padding: 2px 0;
  line-height: 1.5;
  border-bottom: 1px solid var(--border);
}
.ing-item:last-child { border-bottom: none; }

/* Numbered steps */
.step-item {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  align-items: flex-start;
}
.step-num {
  min-width: 22px;
  height: 22px;
  background: var(--green);
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.step-text {
  font-size: 14px;
  color: var(--text);
  line-height: 1.6;
}

/* Health note */
.health-note {
  background: var(--green-bg);
  border-left: 3px solid var(--green);
  border-radius: 0 8px 8px 0;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--green);
  line-height: 1.5;
  margin-top: 4px;
}

/* ══════════════════════════════════════════════════════
   DETECTED INGREDIENT BADGES
══════════════════════════════════════════════════════ */
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0;
}
.ingredient-badge {
  background: var(--green-bg);
  color: var(--green);
  border: 1px solid var(--green-lt);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
}

/* ══════════════════════════════════════════════════════
   EMPTY STATES
══════════════════════════════════════════════════════ */
.empty-state {
  background: var(--card-bg);
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 48px 20px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

/* ══════════════════════════════════════════════════════
   TYPOGRAPHY — fix Streamlit heading/label bleed
══════════════════════════════════════════════════════ */

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
  color: var(--text) !important;
}

[data-testid="stCaptionContainer"] p {
  color: var(--muted) !important;
  font-size: 13px !important;
}

[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stRadio"] label div p,
[data-testid="stSelectbox"] label div p,
[data-testid="stSlider"] label div p,
[data-testid="stTextInput"] label div p {
  color: var(--text) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--text) !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  color: var(--muted) !important;
}

/* ══════════════════════════════════════════════════════
   MISC
══════════════════════════════════════════════════════ */
.section-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 24px 0;
}
.badge {
  display: inline-block;
  background: var(--green-bg);
  color: var(--green);
  border: 1px solid var(--green-lt);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
  margin: 3px;
}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

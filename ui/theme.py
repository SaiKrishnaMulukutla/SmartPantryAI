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
  --radius:     12px;
  --shadow:     0 2px 12px rgba(0,0,0,0.06);
}

/* ── Global ─────────────────────────────────────────── */
html, body, [data-testid="stApp"] {
  background: var(--bg) !important;
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
}

/* ── Auth card ──────────────────────────────────────── */
.auth-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 40px;
  max-width: 440px;
  margin: 60px auto;
  box-shadow: var(--shadow);
}
.auth-card h2 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}
.auth-card .subtitle {
  margin: 0 0 28px;
  font-size: 14px;
  color: var(--muted);
}

/* ── OTP boxes ──────────────────────────────────────── */
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

/* ── Ingredient badge ───────────────────────────────── */
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

/* ── Recipe card ─────────────────────────────────────── */
.recipe-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 16px;
  box-shadow: var(--shadow);
}
.recipe-card h3 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}
.recipe-meta {
  font-size: 13px;
  color: var(--muted);
  margin: 0 0 16px;
}

/* ── Primary button override ─────────────────────────── */
[data-testid="stButton"] button[kind="primary"] {
  background: var(--green) !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  letter-spacing: 0.2px !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
  background: #235c42 !important;
  box-shadow: 0 4px 12px rgba(45,106,79,0.3) !important;
}

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #F6F8F5 !important;
  border-right: 1px solid var(--border) !important;
}

/* ── Input fields ────────────────────────────────────── */
[data-testid="stTextInput"] input {
  border-radius: 8px !important;
  border-color: var(--border) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--green) !important;
  box-shadow: 0 0 0 3px rgba(45,106,79,0.1) !important;
}

/* ── Divider ─────────────────────────────────────────── */
.section-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 24px 0;
}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

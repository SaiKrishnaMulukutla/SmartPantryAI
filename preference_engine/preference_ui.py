from __future__ import annotations

import streamlit as st

from preference_engine.schema import UserPreferences


def render_preference_sidebar() -> UserPreferences:
    """
    Render the user preference widgets in the Streamlit sidebar.
    Returns the current UserPreferences state.
    Persists selections in st.session_state across reruns.
    """
    st.sidebar.title("Your Preferences")
    st.sidebar.markdown("---")

    # ---- Diet ----
    diet_options = {
        "Vegetarian": "veg",
        "Non-Vegetarian": "non_veg",
        "Eggetarian": "eggetarian",
    }
    diet_label = st.sidebar.radio(
        "Diet Type",
        list(diet_options.keys()),
        index=0,
        key="pref_diet",
    )
    diet = diet_options[diet_label]

    st.sidebar.markdown("---")

    # ---- Health ----
    health_options = {
        "Normal": "normal",
        "Diabetic (Low GI)": "diabetic",
        "Low Blood Pressure": "low_bp",
        "High Blood Pressure": "high_bp",
    }
    health_label = st.sidebar.selectbox(
        "Health Condition",
        list(health_options.keys()),
        index=0,
        key="pref_health",
    )
    health = health_options[health_label]

    st.sidebar.markdown("---")

    # ---- Cuisine ----
    cuisine_options = {
        "North Indian": "north_indian",
        "South Indian": "south_indian",
        "Chinese": "chinese",
        "Mediterranean": "mediterranean",
        "Japanese": "japanese",
    }
    cuisine_label = st.sidebar.selectbox(
        "Cuisine Preference",
        list(cuisine_options.keys()),
        index=0,
        key="pref_cuisine",
    )
    cuisine = cuisine_options[cuisine_label]

    st.sidebar.markdown("---")

    # ---- Mood ----
    mood_options = {
        "Tired / Comfort": "tired",
        "Quick Bite": "quick_bite",
        "Romantic": "romantic",
        "Party Mode": "party",
    }
    mood_icons = {
        "Tired / Comfort": "😴",
        "Quick Bite": "⚡",
        "Romantic": "🌹",
        "Party Mode": "🎉",
    }
    mood_label = st.sidebar.radio(
        "Mood",
        list(mood_options.keys()),
        format_func=lambda x: f"{mood_icons[x]}  {x}",
        index=0,
        key="pref_mood",
    )
    mood = mood_options[mood_label]

    st.sidebar.markdown("---")

    # ---- Time ----
    time_minutes = st.sidebar.select_slider(
        "Max Cook Time (minutes)",
        options=[10, 20, 30, 40],
        value=30,
        key="pref_time",
    )

    st.sidebar.markdown("---")

    # ---- Summary pill ----
    prefs = UserPreferences(
        diet=diet,
        health=health,
        cuisine=cuisine,
        mood=mood,
        time_minutes=time_minutes,
    )
    st.sidebar.caption(f"Profile: {prefs.summary()}")

    return prefs

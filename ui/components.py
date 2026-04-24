from __future__ import annotations

import numpy as np
import streamlit as st

from recipe_engine.recipe_parser import Recipe


# ──────────────────────────────────────────────
# Recipe card body (visual only — no save button)
# dashboard.py owns the save interaction
# ──────────────────────────────────────────────

def render_recipe_card_header(recipe: Recipe) -> None:
    """Name + cuisine/time badges."""
    cuisine = recipe.cuisine.replace("_", " ").title()
    st.markdown(
        f"""
        <p class="rc-name">{recipe.name}</p>
        <div>
            <span class="rc-badge rc-badge-green">{cuisine}</span>
            <span class="rc-badge rc-badge-amber">⏱ {recipe.cook_time_minutes} min</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recipe_card_body(recipe: Recipe) -> None:
    """Ingredients / Steps / Notes in tabs — one section visible at a time."""
    tab_labels = ["Ingredients", "Steps"]
    if recipe.health_notes:
        tab_labels.append("Notes")

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        ings_html = "".join(
            f'<div class="ing-item">{item}</div>'
            for item in recipe.ingredients
        )
        st.markdown(ings_html, unsafe_allow_html=True)

    with tabs[1]:
        steps_html = "".join(
            f'<div class="step-item">'
            f'<span class="step-num">{n}</span>'
            f'<span class="step-text">{step}</span>'
            f'</div>'
            for n, step in enumerate(recipe.steps, 1)
        )
        st.markdown(steps_html, unsafe_allow_html=True)

    if recipe.health_notes and len(tabs) == 3:
        with tabs[2]:
            st.markdown(
                f'<div class="health-note">💚 {recipe.health_notes}</div>',
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────
# Detected Ingredient Badges
# ──────────────────────────────────────────────

def render_ingredient_badges(ingredients: list[str]) -> None:
    if not ingredients:
        st.caption("No ingredients detected yet.")
        return
    badges_html = " ".join(
        f'<span class="ingredient-badge">{ing.replace("_", " ").title()}</span>'
        for ing in ingredients
    )
    st.markdown(f'<div class="badge-row">{badges_html}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Detection overlay
# ──────────────────────────────────────────────

def render_detection_overlay(frame_rgb: np.ndarray, caption: str = "") -> None:
    st.image(frame_rgb, caption=caption, use_container_width=True)


# ──────────────────────────────────────────────
# Empty state
# ──────────────────────────────────────────────

def render_empty_state(message: str = "Point your camera at ingredients to get started.") -> None:
    st.markdown(
        f'<div class="empty-state"><p>{message}</p></div>',
        unsafe_allow_html=True,
    )

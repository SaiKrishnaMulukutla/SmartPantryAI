from __future__ import annotations

import numpy as np
import streamlit as st

from recipe_engine.recipe_parser import Recipe


# ──────────────────────────────────────────────
# Recipe Cards
# ──────────────────────────────────────────────

def render_recipe_cards(recipes: list[Recipe]) -> None:
    """Render a vertical stack of recipe cards."""
    if not recipes:
        render_empty_state("No recipes to display.")
        return

    for i, recipe in enumerate(recipes):
        _render_single_card(recipe, index=i)


def _render_single_card(recipe: Recipe, index: int) -> None:
    card_id = f"recipe_card_{index}"

    with st.container():
        st.markdown(
            f"""
            <div class="recipe-card" id="{card_id}">
                <div class="recipe-header">
                    <span class="recipe-title">{recipe.name}</span>
                    <span class="recipe-meta">
                        🍽 {recipe.cuisine} &nbsp;|&nbsp; ⏱ {recipe.cook_time_minutes} min
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Ingredients**")
            for item in recipe.ingredients:
                st.markdown(f"- {item}")

        with col2:
            st.markdown("**Steps**")
            for step_num, step in enumerate(recipe.steps, start=1):
                st.markdown(f"{step_num}. {step}")

        if recipe.health_notes:
            st.info(f"Health note: {recipe.health_notes}", icon="💊")

        st.markdown("<hr class='recipe-divider'>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Detected Ingredient Badges
# ──────────────────────────────────────────────

def render_ingredient_badges(ingredients: list[str]) -> None:
    """Render detected ingredients as horizontal badge pills."""
    if not ingredients:
        st.caption("No ingredients detected yet.")
        return

    badges_html = " ".join(
        f'<span class="ingredient-badge">{ing.replace("_", " ").title()}</span>'
        for ing in ingredients
    )
    st.markdown(
        f'<div class="badge-row">{badges_html}</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# Detection Overlay (annotated frame)
# ──────────────────────────────────────────────

def render_detection_overlay(frame_rgb: np.ndarray, caption: str = "") -> None:
    """Display an annotated RGB frame using st.image."""
    st.image(frame_rgb, caption=caption, use_container_width=True)


# ──────────────────────────────────────────────
# Empty / error states
# ──────────────────────────────────────────────

def render_empty_state(message: str = "Point your camera at ingredients to get started.") -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

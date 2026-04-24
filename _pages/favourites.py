"""Favourites page."""
from __future__ import annotations

import streamlit as st

from auth.session import current_user_id
from db.favourites import get_favourites, remove_favourite


def render() -> None:
    st.title("❤️ Saved Recipes")
    st.caption("Your favourite recipes, saved for later")

    uid = current_user_id()
    if not uid:
        st.error("Not authenticated.")
        return

    favs = get_favourites(uid)
    if not favs:
        st.info("No saved recipes yet. Hit the 🤍 button on any recipe to save it here.")
        return

    for fav in favs:
        recipe = fav.get("recipe", {})
        with st.expander(f"🍽️ {fav['recipe_name']}", expanded=False):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{recipe.get('cuisine', '')}** · ⏱️ {recipe.get('cook_time_minutes', '?')} min")
            with col2:
                if st.button("❌ Remove", key=f"rm_{fav['id']}", use_container_width=True):
                    remove_favourite(uid, fav["recipe_name"])
                    st.rerun()

            if recipe.get("ingredients"):
                st.markdown("**Ingredients**")
                for ing in recipe["ingredients"]:
                    st.markdown(f"- {ing}")

            if recipe.get("steps"):
                st.markdown("**Steps**")
                for i, step in enumerate(recipe["steps"], 1):
                    st.markdown(f"{i}. {step}")

            if recipe.get("health_notes"):
                st.info(f"💚 {recipe['health_notes']}")

"""Recipe history page."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from auth.session import current_user_id
from db.history import delete_history_entry, get_history


def render() -> None:
    st.title("📖 Recipe History")
    st.caption("All your past ingredient detections and generated recipes")

    uid = current_user_id()
    if not uid:
        st.error("Not authenticated.")
        return

    entries = get_history(uid)
    if not entries:
        st.info("No history yet. Go detect some ingredients and generate recipes!")
        return

    for entry in entries:
        ts = datetime.fromisoformat(entry["created_at"]).astimezone()
        label = ts.strftime("%d %b %Y, %I:%M %p")
        ingredients = entry.get("ingredients", [])
        recipes = entry.get("recipes", [])

        with st.expander(f"🕐 {label} — {', '.join(ingredients[:4])}{'…' if len(ingredients) > 4 else ''}"):
            st.markdown(f"**Detected:** {', '.join(ingredients)}")
            st.markdown(f"**Recipes generated:** {len(recipes)}")
            for r in recipes:
                st.markdown(f"&nbsp;&nbsp;🍽️ **{r.get('name', 'Unknown')}** — {r.get('cuisine', '')} · {r.get('cook_time_minutes', '?')} min")

            if st.button("🗑️ Delete", key=f"del_{entry['id']}"):
                delete_history_entry(entry["id"])
                st.rerun()

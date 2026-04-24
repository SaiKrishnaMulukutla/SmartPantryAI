"""User preferences CRUD — upserts on every save."""
from __future__ import annotations

from typing import Any

from db.client import supabase


_DEFAULTS = {
    "diet": "veg",
    "health": "normal",
    "cuisine": "north_indian",
    "mood": "tired",
    "time_minutes": 30,
}


def get_preferences(user_id: str) -> dict[str, Any]:
    res = supabase.table("preferences").select("*").eq("user_id", user_id).maybe_single().execute()
    return (res.data or {**_DEFAULTS, "user_id": user_id}) if res else {**_DEFAULTS, "user_id": user_id}


def save_preferences(user_id: str, prefs: dict[str, Any]) -> None:
    supabase.table("preferences").upsert({
        "user_id": user_id,
        **{k: prefs[k] for k in _DEFAULTS if k in prefs},
    }).execute()

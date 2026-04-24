"""Recipe history CRUD."""
from __future__ import annotations

import json
from typing import Any

from db.client import supabase


def save_history(user_id: str, ingredients: list[str], recipes: list[dict]) -> None:
    supabase.table("recipe_history").insert({
        "user_id": user_id,
        "ingredients": ingredients,
        "recipes": recipes,
    }).execute()


def get_history(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    res = (
        supabase.table("recipe_history")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return (res.data or []) if res else []


def delete_history_entry(entry_id: str) -> None:
    supabase.table("recipe_history").delete().eq("id", entry_id).execute()

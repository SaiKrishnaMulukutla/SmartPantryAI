"""Favourites CRUD."""
from __future__ import annotations

from typing import Any

from db.client import supabase


def add_favourite(user_id: str, recipe_name: str, recipe: dict) -> None:
    supabase.table("favourites").insert({
        "user_id": user_id,
        "recipe_name": recipe_name,
        "recipe": recipe,
    }).execute()


def remove_favourite(user_id: str, recipe_name: str) -> None:
    supabase.table("favourites").delete().eq("user_id", user_id).eq("recipe_name", recipe_name).execute()


def get_favourites(user_id: str) -> list[dict[str, Any]]:
    res = (
        supabase.table("favourites")
        .select("*")
        .eq("user_id", user_id)
        .order("saved_at", desc=True)
        .execute()
    )
    return (res.data or []) if res else []


def is_favourite(user_id: str, recipe_name: str) -> bool:
    res = (
        supabase.table("favourites")
        .select("id")
        .eq("user_id", user_id)
        .eq("recipe_name", recipe_name)
        .maybe_single()
        .execute()
    )
    return bool(res and res.data)

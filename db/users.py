"""User CRUD — no Streamlit imports."""
from __future__ import annotations

from typing import Any

from db.client import supabase


def create_user(email: str, password_hash: str, name: str = "") -> dict[str, Any]:
    res = supabase.table("users").insert({
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "is_verified": False,
    }).execute()
    return res.data[0]


def get_user_by_email(email: str) -> dict[str, Any] | None:
    res = supabase.table("users").select("*").eq("email", email).maybe_single().execute()
    return res.data if res else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    res = supabase.table("users").select("*").eq("id", user_id).maybe_single().execute()
    return res.data if res else None


def mark_verified(email: str) -> None:
    supabase.table("users").update({"is_verified": True}).eq("email", email).execute()


def update_password(email: str, new_hash: str) -> None:
    supabase.table("users").update({"password_hash": new_hash}).eq("email", email).execute()


def email_exists(email: str) -> bool:
    return get_user_by_email(email) is not None

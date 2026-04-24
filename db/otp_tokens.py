"""OTP token storage in Supabase (survives page refreshes)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from db.client import supabase

_TTL_MINUTES = 10


def store_otp(email: str, otp: str) -> None:
    # Invalidate any existing tokens for this email first
    supabase.table("otp_tokens").update({"used": True}).eq("email", email).execute()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=_TTL_MINUTES)).isoformat()
    supabase.table("otp_tokens").insert({
        "email": email,
        "otp": otp,
        "expires_at": expires_at,
        "used": False,
    }).execute()


def verify_otp(email: str, otp: str) -> bool:
    res = (
        supabase.table("otp_tokens")
        .select("*")
        .eq("email", email)
        .eq("otp", otp)
        .eq("used", False)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return False
    expires_at = datetime.fromisoformat(res.data["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        return False
    supabase.table("otp_tokens").update({"used": True}).eq("id", res.data["id"]).execute()
    return True

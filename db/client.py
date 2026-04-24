"""Supabase client singleton — import `supabase` from here everywhere."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from supabase import Client, create_client

_URL = os.environ["SUPABASE_URL"]
_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(_URL, _KEY)
    return _client


supabase: Client = get_client()

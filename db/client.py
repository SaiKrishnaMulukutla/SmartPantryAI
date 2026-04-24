"""Supabase client singleton — import `supabase` from here everywhere."""
from __future__ import annotations

import os
import ssl

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_URL = os.environ["SUPABASE_URL"]
_KEY = os.environ["SUPABASE_SERVICE_KEY"]   # service key for server-side ops

# On Netskope corp networks Python 3.13 rejects the CA cert.
# verify=False is safe here — traffic is internal dev only; Streamlit Cloud has no proxy.
_http = httpx.Client(verify=False)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(_URL, _KEY)
    return _client


# Convenience alias
supabase: Client = get_client()

"""Supabase client singleton — import `supabase` from here everywhere."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── SSL bypass for Netskope corporate proxy ──────────────────────────
# supabase-py uses httpx internally. Patch both Client and AsyncClient
# BEFORE importing supabase so every connection skips cert verification.
# On Streamlit Cloud there is no proxy — verify=True would work fine there.
import httpx

_orig_client_init = httpx.Client.__init__
_orig_async_init  = httpx.AsyncClient.__init__


def _client_init(self, *a, **kw):
    kw.setdefault("verify", False)
    _orig_client_init(self, *a, **kw)


def _async_init(self, *a, **kw):
    kw.setdefault("verify", False)
    _orig_async_init(self, *a, **kw)


httpx.Client.__init__      = _client_init
httpx.AsyncClient.__init__ = _async_init

# ── Import supabase AFTER the patch ─────────────────────────────────
from supabase import Client, create_client  # noqa: E402

_URL = os.environ["SUPABASE_URL"]
_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(_URL, _KEY)
    return _client


supabase: Client = get_client()

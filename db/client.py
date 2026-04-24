"""Supabase client singleton — import `supabase` from here everywhere."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── SSL bypass for Netskope corporate proxy ──────────────────────────
# supabase-py sub-packages (gotrue, postgrest, storage3, functions) all
# pass verify=True explicitly to httpx.Client() — so setdefault() was
# silently ignored.  We must force-override via kw["verify"] = False.
#
# Guard: only patch when REQUESTS_CA_BUNDLE is set (Netskope sets it
# automatically on corporate machines).  On Streamlit Cloud it is unset,
# so the patch is skipped and normal TLS verification applies.
import httpx

if os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("DISABLE_SSL_VERIFY"):
    _orig_client_init = httpx.Client.__init__
    _orig_async_init  = httpx.AsyncClient.__init__

    def _client_init(self, *a, **kw):
        kw["verify"] = False          # force-override, not setdefault
        _orig_client_init(self, *a, **kw)

    def _async_init(self, *a, **kw):
        kw["verify"] = False
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

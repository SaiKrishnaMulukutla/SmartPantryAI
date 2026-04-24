"""Supabase client singleton — import `supabase` from here everywhere."""
from __future__ import annotations

import os
import ssl

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Corporate proxy SSL fix ───────────────────────────────────────────
# Python 3.13 sets VERIFY_X509_STRICT by default. Netskope's CA cert
# lacks the keyUsage extension required by RFC 5280, so it fails.
# We build a context that still verifies the full chain (using certifi,
# which now includes the Netskope CA) but drops the strict extension check.
# Guard: only patch when REQUESTS_CA_BUNDLE is present (corporate network).
# On Streamlit Cloud the env var is absent and this block is skipped.
if os.environ.get("REQUESTS_CA_BUNDLE"):
    _ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    _ssl_ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

    _orig_client_init = httpx.Client.__init__
    _orig_async_init  = httpx.AsyncClient.__init__

    def _client_init(self, *a, **kw):
        kw["verify"] = _ssl_ctx
        _orig_client_init(self, *a, **kw)

    def _async_init(self, *a, **kw):
        kw["verify"] = _ssl_ctx
        _orig_async_init(self, *a, **kw)

    httpx.Client.__init__      = _client_init
    httpx.AsyncClient.__init__ = _async_init

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

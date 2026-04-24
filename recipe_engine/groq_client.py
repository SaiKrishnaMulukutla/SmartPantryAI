from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from groq import AsyncGroq, Groq

from preference_engine.schema import UserPreferences
from recipe_engine.prompt_builder import build_prompt
from recipe_engine.recipe_parser import Recipe, parse_groq_response


_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 3000


class GroqRecipeClient:
    """
    Async-first Groq API wrapper for recipe generation.

    Usage (async):
        client = GroqRecipeClient(api_key="...")
        recipes = await client.get_recipes(ingredients, preferences)

    Usage (sync, e.g. inside Streamlit):
        recipes = client.get_recipes_sync(ingredients, preferences)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY in your .env file "
                "or pass it explicitly to GroqRecipeClient()."
            )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Python 3.13 enforces RFC 5280 keyUsage — Netskope CA cert fails this check.
        # Disable verification for local dev; on cloud (Streamlit) no proxy exists.
        _verify = not bool(os.getenv("REQUESTS_CA_BUNDLE"))
        http_client = httpx.Client(verify=False if not _verify else True)
        async_http_client = httpx.AsyncClient(verify=False if not _verify else True)
        self._async_client = AsyncGroq(api_key=resolved_key, http_client=async_http_client)
        self._sync_client = Groq(api_key=resolved_key, http_client=http_client)

    # ------------------------------------------------------------------
    # Async interface
    # ------------------------------------------------------------------

    async def get_recipes(
        self,
        ingredients: list[str],
        preferences: UserPreferences,
        max_recipes: int = 3,
    ) -> list[Recipe]:
        """Call Groq asynchronously and return parsed Recipe objects."""
        prompt = build_prompt(ingredients, preferences, max_recipes)
        raw = await self._async_chat(prompt)
        return parse_groq_response(raw)

    async def _async_chat(self, prompt: str) -> str:
        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Sync interface (Streamlit-friendly)
    # ------------------------------------------------------------------

    def get_recipes_sync(
        self,
        ingredients: list[str],
        preferences: UserPreferences,
        max_recipes: int = 3,
    ) -> list[Recipe]:
        """
        Synchronous wrapper — safe to call from Streamlit callbacks
        without needing an event loop.
        """
        prompt = build_prompt(ingredients, preferences, max_recipes)
        raw = self._sync_chat(prompt)
        return parse_groq_response(raw)

    def _sync_chat(self, prompt: str) -> str:
        response = self._sync_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, **kwargs: Any) -> "GroqRecipeClient":
        """Convenience factory: reads GROQ_API_KEY from environment."""
        return cls(api_key=os.getenv("GROQ_API_KEY"), **kwargs)

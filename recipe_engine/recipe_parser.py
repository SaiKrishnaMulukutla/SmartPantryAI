from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError


class Recipe(BaseModel):
    name: str
    cuisine: str
    cook_time_minutes: int = Field(ge=1, le=120)
    ingredients: list[str] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    health_notes: str = ""


def parse_groq_response(raw_response: str) -> list[Recipe]:
    """
    Parse and validate the Groq API JSON output into a list of Recipe objects.

    Handles three common LLM output issues:
    1. JSON wrapped in markdown code fences (```json ... ```)
    2. Extra text before/after the JSON array
    3. Malformed JSON — falls back gracefully with a warning recipe
    """
    if not raw_response or not raw_response.strip():
        return [_error_recipe("Groq returned an empty response.")]

    cleaned = _extract_json(raw_response)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return [_error_recipe(f"JSON decode error: {exc}\n\nRaw output:\n{raw_response[:500]}")]

    if not isinstance(data, list):
        # Some models return a single object instead of an array
        data = [data]

    recipes: list[Recipe] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            recipes.append(Recipe(**item))
        except (ValidationError, TypeError) as exc:
            # Skip malformed entries; add a warning placeholder
            recipes.append(_error_recipe(f"Recipe validation failed: {exc}"))

    return recipes if recipes else [_error_recipe("No valid recipes found in the response.")]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the first JSON array from text."""
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)

    # Find the first '[' ... ']' block
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text.strip()


def _error_recipe(message: str) -> Recipe:
    return Recipe(
        name="⚠ Recipe Unavailable",
        cuisine="—",
        cook_time_minutes=1,
        ingredients=["—"],
        steps=[message],
        health_notes="",
    )

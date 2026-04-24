from __future__ import annotations

from preference_engine.schema import UserPreferences


# Health-condition dietary notes injected into every prompt
_HEALTH_NOTES: dict[str, str] = {
    "normal": "No specific dietary restrictions.",
    "diabetic": (
        "User is diabetic: prefer low-GI ingredients, avoid refined carbs, "
        "white rice, white bread, and added sugar. Favour whole grains, legumes, "
        "and fibre-rich vegetables."
    ),
    "low_bp": (
        "User has low blood pressure: include moderate sodium where appropriate, "
        "and ingredients like beetroot, carrots, and leafy greens that support "
        "healthy circulation."
    ),
    "high_bp": (
        "User has high blood pressure: strictly low sodium, heart-healthy fats "
        "(olive oil, nuts), no processed or heavily salted ingredients."
    ),
}

_MOOD_NOTES: dict[str, str] = {
    "party": "Make it impressive — multi-component, crowd-pleasing, visually striking.",
    "tired": "Keep it simple and comforting — ideally a one-pot or minimal-step dish.",
    "romantic": "Make it elegant and plated — moderate complexity, thoughtful presentation.",
    "quick_bite": "Snack-level simplicity — 1–2 ingredients, little or no cooking required.",
}

_RECIPE_SCHEMA = """[
  {
    "name": "string",
    "cuisine": "string",
    "cook_time_minutes": number,
    "ingredients": ["string"],
    "steps": ["string"],
    "health_notes": "string"
  }
]"""


def build_prompt(
    ingredients: list[str],
    preferences: UserPreferences,
    max_recipes: int = 3,
) -> str:
    """
    Construct a structured prompt for the Groq API.

    Returns a prompt that instructs Llama 3 to output a JSON array
    of recipes matching the detected ingredients and user profile.
    """
    if not ingredients:
        raise ValueError("Cannot build a recipe prompt with an empty ingredient list.")

    ingredient_list = ", ".join(ingredients)
    health_note = _HEALTH_NOTES[preferences.health]
    mood_note = _MOOD_NOTES[preferences.mood]
    cuisine_label = preferences.cuisine_label()
    diet_label = preferences.diet_label()

    prompt = f"""You are a professional chef and nutritionist.

Given the detected ingredients and user preferences below, suggest up to {max_recipes} recipes.

---
DETECTED INGREDIENTS: {ingredient_list}

USER PROFILE:
- Diet: {diet_label}
- Health: {health_note}
- Cuisine preference: {cuisine_label}
- Mood: {mood_note}
- Max cook time: {preferences.time_minutes} minutes

RULES:
1. Only use ingredients from the detected list (you may add common pantry staples like oil, salt, water, basic spices).
2. Every recipe MUST fit within {preferences.time_minutes} minutes total.
3. Respect the diet strictly: {"no meat, fish, or eggs" if preferences.diet == "veg" else "eggs are allowed but no meat or fish" if preferences.diet == "eggetarian" else "all ingredients are allowed"}.
4. Match the cuisine style: {cuisine_label}.
5. Steps must be detailed and actionable — include quantities, timings, temperatures, and technique tips. Aim for 6–10 steps per recipe.
6. ingredients list should include quantities (e.g. "2 medium tomatoes, chopped").
7. health_notes should explain in 2–3 sentences why this recipe suits the user's health profile.
---

Respond ONLY with a valid JSON array — no markdown, no explanation, no extra text.
Use exactly this schema:

{_RECIPE_SCHEMA}
"""
    return prompt.strip()

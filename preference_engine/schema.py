from typing import Literal
from pydantic import BaseModel


Diet = Literal["veg", "non_veg", "eggetarian"]
Health = Literal["normal", "diabetic", "low_bp", "high_bp"]
Cuisine = Literal["north_indian", "south_indian", "chinese", "mediterranean", "japanese"]
Mood = Literal["party", "tired", "romantic", "quick_bite"]
TimeConstraint = Literal[10, 20, 30, 40]


class UserPreferences(BaseModel):
    diet: Diet = "veg"
    health: Health = "normal"
    cuisine: Cuisine = "north_indian"
    mood: Mood = "tired"
    time_minutes: TimeConstraint = 30

    # Human-readable labels for UI display
    DIET_LABELS: dict = {
        "veg": "Vegetarian",
        "non_veg": "Non-Vegetarian",
        "eggetarian": "Eggetarian",
    }
    HEALTH_LABELS: dict = {
        "normal": "Normal",
        "diabetic": "Diabetic (Low GI)",
        "low_bp": "Low Blood Pressure",
        "high_bp": "High Blood Pressure",
    }
    CUISINE_LABELS: dict = {
        "north_indian": "North Indian",
        "south_indian": "South Indian",
        "chinese": "Chinese",
        "mediterranean": "Mediterranean",
        "japanese": "Japanese",
    }
    MOOD_LABELS: dict = {
        "party": "Party Mode",
        "tired": "Tired / Comfort",
        "romantic": "Romantic",
        "quick_bite": "Quick Bite",
    }

    model_config = {"arbitrary_types_allowed": True}

    def diet_label(self) -> str:
        return self.DIET_LABELS.get(self.diet, self.diet)

    def health_label(self) -> str:
        return self.HEALTH_LABELS.get(self.health, self.health)

    def cuisine_label(self) -> str:
        return self.CUISINE_LABELS.get(self.cuisine, self.cuisine)

    def mood_label(self) -> str:
        return self.MOOD_LABELS.get(self.mood, self.mood)

    def summary(self) -> str:
        return (
            f"{self.diet_label()} · {self.health_label()} · "
            f"{self.cuisine_label()} · {self.mood_label()} · "
            f"{self.time_minutes} min"
        )

    @classmethod
    def from_dict(cls, d: dict) -> "UserPreferences":
        return cls.model_validate(d)

    def to_dict(self) -> dict:
        return self.model_dump(include={"diet", "health", "cuisine", "mood", "time_minutes"})

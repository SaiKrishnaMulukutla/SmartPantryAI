"""Main dashboard — ingredient detection + recipe generation."""
from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

from auth.session import current_user_id, current_email
from db.history import save_history
from db.favourites import add_favourite, remove_favourite, is_favourite
from detection.model import YOLODetector, InferenceResult, run_inference
from ui.preference_widget import render_preference_sidebar
from recipe_engine.groq_client import GroqRecipeClient
from recipe_engine.recipe_parser import Recipe
from ui.components import (
    render_detection_overlay, render_ingredient_badges, render_empty_state,
    render_recipe_card_header, render_recipe_card_body,
)

_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/food_yolo11/best.pt")
_CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
_MAX_RECIPES = int(os.getenv("MAX_RECIPES", "3"))


@st.cache_resource(show_spinner="Loading YOLO model…")
def _load_detector() -> YOLODetector:
    if os.path.exists(_MODEL_PATH):
        return YOLODetector(_MODEL_PATH, confidence=_CONFIDENCE)
    st.warning(f"Custom model not found at `{_MODEL_PATH}`. Using pretrained checkpoint.", icon="⚠️")
    return YOLODetector.from_pretrained("yolo11n.pt", confidence=_CONFIDENCE)


@st.cache_resource(show_spinner="Connecting to Groq…")
def _load_groq() -> GroqRecipeClient | None:
    key = os.getenv("GROQ_API_KEY")
    return GroqRecipeClient(api_key=key) if key else None


def _init() -> None:
    for k, v in {
        "detections": [],
        "last_ingredients": [],
        "recipes": [],
        "frame_rgb": None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render() -> None:
    _init()
    preferences = render_preference_sidebar()

    st.title("🍳 SmartPantryAI")
    st.caption("Snap or upload ingredients → AI detects → personalised recipes")
    st.markdown("<div style='margin-bottom:24px'></div>", unsafe_allow_html=True)

    cam_col, recipe_col = st.columns([1, 1], gap="large")

    # ── Left: Detection ──────────────────────────────────────────────────
    with cam_col:
        st.subheader("Ingredient Detection")

        tab_cam, tab_upload = st.tabs(["📷 Camera", "🖼️ Upload"])
        image_data = None

        with tab_cam:
            snapshot = st.camera_input("Point camera at ingredients")
            if snapshot:
                image_data = snapshot.getvalue()

        with tab_upload:
            uploaded = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "webp"],
                                        label_visibility="collapsed")
            if uploaded:
                image_data = uploaded.getvalue()

        # Run detection
        if image_data:
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            frame_rgb = np.array(img)
            result: InferenceResult = run_inference(_load_detector(), frame_rgb)

            st.session_state.frame_rgb = result.annotated_image
            st.session_state.last_ingredients = result.labels

            render_detection_overlay(result.annotated_image)
        elif st.session_state.frame_rgb is not None:
            render_detection_overlay(st.session_state.frame_rgb, caption="Last captured frame")
        else:
            render_empty_state("Capture or upload a photo to detect ingredients.")

        get_recipes_btn = st.button(
            "✨ Get Recipes",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.last_ingredients,
        )

        if st.session_state.last_ingredients:
            st.markdown("**Detected Ingredients**")
            render_ingredient_badges(st.session_state.last_ingredients)

    # ── Right: Recipes ───────────────────────────────────────────────────
    with recipe_col:
        st.subheader("Recipe Suggestions")

        if get_recipes_btn:
            client = _load_groq()
            if not client:
                st.error("GROQ_API_KEY not set in .env", icon="🔑")
            else:
                ingredients = st.session_state.last_ingredients
                with st.spinner(f"Generating recipes for: {', '.join(ingredients)}…"):
                    try:
                        recipes: list[Recipe] = client.get_recipes_sync(
                            ingredients, preferences, max_recipes=_MAX_RECIPES
                        )
                        st.session_state.recipes = recipes
                        # Save to history
                        uid = current_user_id()
                        if uid:
                            save_history(uid, ingredients, [r.model_dump() for r in recipes])
                    except Exception as exc:
                        st.error(f"Groq error: {exc}", icon="❌")

        if st.session_state.recipes:
            _render_recipes(st.session_state.recipes)
        else:
            render_empty_state("Detect ingredients and click 'Get Recipes'.")


def _render_recipes(recipes: list[Recipe]) -> None:
    uid = current_user_id()
    for recipe in recipes:
        with st.container(border=True):
            # Header row: name + badges on left, save button on right
            col_info, col_action = st.columns([5, 1])
            with col_info:
                render_recipe_card_header(recipe)
            with col_action:
                if uid:
                    fav = is_favourite(uid, recipe.name)
                    heart = "❤️" if fav else "🤍"
                    if st.button(heart, key=f"fav_{recipe.name}", use_container_width=True,
                                 help="Remove from favourites" if fav else "Save to favourites"):
                        if fav:
                            remove_favourite(uid, recipe.name)
                        else:
                            add_favourite(uid, recipe.name, recipe.model_dump())
                        st.rerun()

            st.divider()
            render_recipe_card_body(recipe)

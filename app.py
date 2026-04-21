from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ──────────────────────
st.set_page_config(
    page_title="AI Recipe Recommender",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject custom CSS ───────────────────────────────────────────────
_CSS_PATH = Path(__file__).parent / "ui" / "styles.css"
if _CSS_PATH.exists():
    st.markdown(f"<style>{_CSS_PATH.read_text()}</style>", unsafe_allow_html=True)

# ── Local imports (after dotenv + page config) ──────────────────────
from detector.yolo_detector import YOLODetector, Detection
from detector.frame_processor import FrameProcessor
from preference_engine.preference_ui import render_preference_sidebar
from recipe_engine.groq_client import GroqRecipeClient
from recipe_engine.recipe_parser import Recipe
from ui.components import (
    render_recipe_cards,
    render_detection_overlay,
    render_ingredient_badges,
    render_empty_state,
)


# ── Constants ───────────────────────────────────────────────────────
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/food_yolo11/best.pt")
CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
MAX_RECIPES = int(os.getenv("MAX_RECIPES", "3"))
CAMERA_INDEX = 0


# ── Cached resource loaders ─────────────────────────────────────────

@st.cache_resource(show_spinner="Loading YOLO model…")
def load_detector() -> YOLODetector:
    if os.path.exists(MODEL_PATH):
        return YOLODetector(MODEL_PATH, confidence=CONFIDENCE)
    # Fall back to pretrained checkpoint for testing before fine-tuning
    st.warning(
        f"Custom model not found at `{MODEL_PATH}`. "
        "Loading pretrained `yolo11m.pt` instead. "
        "Train and place your model to detect food ingredients accurately.",
        icon="⚠️",
    )
    return YOLODetector.from_pretrained("yolo11m.pt", confidence=CONFIDENCE)


@st.cache_resource(show_spinner="Connecting to Groq…")
def load_groq_client() -> GroqRecipeClient | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return GroqRecipeClient(api_key=api_key)


# ── Session state defaults ──────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "camera_running": False,
        "detections": [],
        "last_ingredients": [],
        "recipes": [],
        "frame_rgb": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Main layout ─────────────────────────────────────────────────────

def main() -> None:
    _init_state()

    # Sidebar — preferences
    preferences = render_preference_sidebar()

    # Header
    st.title("🍳 AI Recipe Recommender")
    st.caption("Point your camera at ingredients → get personalized recipes powered by YOLOv11 + Groq Llama 3")

    # Two-column layout
    cam_col, recipe_col = st.columns([1, 1], gap="large")

    # ── Left column: Camera feed ────────────────────────────────────
    with cam_col:
        st.subheader("Live Ingredient Detection")

        ctrl_col1, ctrl_col2 = st.columns(2)
        with ctrl_col1:
            if st.button(
                "Stop Camera" if st.session_state.camera_running else "Start Camera",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.camera_running = not st.session_state.camera_running
                if not st.session_state.camera_running:
                    st.session_state.frame_rgb = None

        with ctrl_col2:
            get_recipes_btn = st.button(
                "Get Recipes",
                type="primary",
                use_container_width=True,
                disabled=not st.session_state.last_ingredients,
            )

        # Frame display placeholder
        frame_placeholder = st.empty()

        # Detected ingredients
        st.markdown("**Detected Ingredients**")
        ingredient_placeholder = st.empty()

        # ── Camera loop ─────────────────────────────────────────────
        if st.session_state.camera_running:
            detector = load_detector()
            processor = FrameProcessor(camera_index=CAMERA_INDEX)

            try:
                processor.open()
                while st.session_state.camera_running:
                    frame_bgr = processor.read_frame()
                    if frame_bgr is None:
                        st.error("Camera read failed. Check that your webcam is connected.")
                        st.session_state.camera_running = False
                        break

                    detections: list[Detection] = detector.detect(frame_bgr)
                    annotated_bgr = detector.draw_boxes(frame_bgr, detections)
                    frame_rgb = processor.bgr_to_rgb(annotated_bgr)

                    st.session_state.frame_rgb = frame_rgb
                    st.session_state.detections = detections
                    st.session_state.last_ingredients = detector.unique_labels(detections)

                    with frame_placeholder:
                        render_detection_overlay(frame_rgb)

                    with ingredient_placeholder:
                        render_ingredient_badges(st.session_state.last_ingredients)

                    time.sleep(0.04)  # ~25 fps cap
                    st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))
                st.session_state.camera_running = False
            finally:
                processor.close()

        else:
            # Show last captured frame or placeholder
            with frame_placeholder:
                if st.session_state.frame_rgb is not None:
                    render_detection_overlay(st.session_state.frame_rgb, caption="Last captured frame")
                else:
                    render_empty_state("Click 'Start Camera' to begin live detection.")

            with ingredient_placeholder:
                render_ingredient_badges(st.session_state.last_ingredients)

    # ── Right column: Recipes ───────────────────────────────────────
    with recipe_col:
        st.subheader("Recipe Suggestions")

        if get_recipes_btn:
            _fetch_and_display_recipes(preferences)
        else:
            if st.session_state.recipes:
                render_recipe_cards(st.session_state.recipes)
            else:
                render_empty_state(
                    "Detect some ingredients and click 'Get Recipes' to see suggestions here."
                )


def _fetch_and_display_recipes(preferences) -> None:
    client = load_groq_client()
    if client is None:
        st.error(
            "GROQ_API_KEY is not set. Add it to your `.env` file and restart the app.",
            icon="🔑",
        )
        return

    ingredients = st.session_state.last_ingredients
    if not ingredients:
        st.warning("No ingredients detected yet. Start the camera and point it at some food.")
        return

    with st.spinner(f"Generating recipes for: {', '.join(ingredients)}…"):
        try:
            recipes: list[Recipe] = client.get_recipes_sync(
                ingredients, preferences, max_recipes=MAX_RECIPES
            )
            st.session_state.recipes = recipes
        except Exception as exc:
            st.error(f"Groq API error: {exc}", icon="❌")
            return

    render_recipe_cards(st.session_state.recipes)


if __name__ == "__main__":
    main()

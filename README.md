# SmartPantryAI — AI Recipe Recommendation System

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![YOLOv11](https://img.shields.io/badge/YOLO-v11-orange)
![Groq](https://img.shields.io/badge/Groq-Llama%203%2070B-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?logo=streamlit)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv)
![Dataset](https://img.shields.io/badge/Dataset-36%2C503%20images-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> An end-to-end computer vision pipeline that detects food ingredients from a live camera feed and generates personalized, context-aware recipe recommendations — powered by YOLOv11 and the Groq API (Llama 3).

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [User Preference Engine](#user-preference-engine)
- [Project Structure](#project-structure)
- [Dataset & Training](#dataset--training)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [API Reference](#api-reference)
- [Build Status](#build-status)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

**SmartPantryAI** bridges computer vision and generative AI to answer: *"What can I cook with what I have right now?"*

Point your camera at ingredients on your kitchen counter. The system detects them in real time using YOLOv11, cross-references your personal dietary profile, and calls Groq's ultra-fast inference API to generate tailored recipe suggestions — all in under a second.

---

## Key Features

| Feature | Description |
|---|---|
| **Real-time Ingredient Detection** | YOLOv11 identifies 30 food items from a live webcam feed via OpenCV |
| **Context-Aware Recipe Generation** | Groq API (Llama 3 70B) crafts structured recipes using detected ingredients and user preferences |
| **User Preference Engine** | 5-dimensional preference profile: diet, health, cuisine, mood, time |
| **Streamlit Web UI** | Clean browser interface with live video, ingredient overlay, and recipe cards |
| **Sub-second Inference** | Groq's LPU-powered inference delivers recipes in ~200–400ms |
| **Kaggle Training Pipeline** | Fully automated training on free T4 GPU via Kaggle API |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Web App                        │
│  ┌───────────────────────┐              ┌────────────────────┐  │
│  │   Webcam Feed         │              │   Recipe Display   │  │
│  │   (OpenCV)            │              │   (Cards + Steps)  │  │
│  └───────────┬───────────┘              └─────────┬──────────┘  │
└──────────────┼───────────────────────────────────┼─────────────┘
               ▼                                   ▲
┌──────────────────────────┐       ┌───────────────────────────┐
│   YOLOv11 Detector       │       │      Groq API             │
│                          ├──────▶│   (Llama 3 - 70B)         │
│  Input:  Video frames    │       │                           │
│  Output: Ingredient      │       │  Input:  Ingredients +    │
│          labels +        │       │          User Profile     │
│          bounding boxes  │       │  Output: Recipe JSON      │
└──────────────────────────┘       └───────────────────────────┘
               ▲
┌──────────────────────────┐
│  User Preference Engine  │
│  - Diet type             │
│  - Health condition      │
│  - Cuisine preference    │
│  - Current mood          │
│  - Time constraint       │
└──────────────────────────┘
```

### Data Flow

```
Camera Frame → OpenCV → YOLOv11 → Ingredient List ──┐
                                                      ├──▶ Prompt Builder ──▶ Groq API ──▶ Recipe Cards
                              User Preference Profile ┘
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Object Detection | YOLOv11 (Ultralytics 8.4+) | Real-time food ingredient detection |
| Video Capture | OpenCV 4.x | Webcam feed and frame preprocessing |
| LLM Inference | Groq API + Llama 3 (70B) | Context-aware recipe generation |
| Web Interface | Streamlit 1.56 | Interactive UI with live video stream |
| Language | Python 3.13 | Core application language |
| Model Training | Ultralytics CLI + Kaggle API | Fine-tuning YOLO on 36,503 food images |
| Data Labeling | Roboflow + Mendeley | Dataset annotation and augmentation |

---

## User Preference Engine

The preference engine builds a structured profile injected into every Groq prompt, ensuring recipes are ingredient-driven and truly personalized.

### Preference Dimensions

#### 1. Diet Type
| Option | Description |
|---|---|
| `veg` | Strictly vegetarian — no meat, fish, or eggs |
| `non_veg` | All ingredients allowed |
| `eggetarian` | Vegetarian + eggs, no meat or fish |

#### 2. Health Condition
| Option | Dietary Impact |
|---|---|
| `normal` | No restrictions |
| `diabetic` | Low GI, reduced sugar/refined carbs |
| `low_bp` | Salt-aware, sodium-supporting ingredients |
| `high_bp` | Strictly low sodium, heart-healthy fats |

#### 3. Cuisine Preference
`north_indian` · `south_indian` · `chinese` · `mediterranean` · `japanese`

#### 4. Mood
`party` · `tired` · `romantic` · `quick_bite`

#### 5. Time Constraint
`10` · `20` · `30` · `40` minutes

---

## Project Structure

```
yolo/
├── app.py                          # Streamlit entry point
├── requirements.txt
├── .env                            # API keys — never commit
├── .gitignore
│
├── detector/
│   ├── yolo_detector.py            # YOLOv11 inference wrapper
│   └── frame_processor.py         # OpenCV webcam + preprocessing
│
├── preference_engine/
│   ├── schema.py                   # Pydantic models (UserPreferences)
│   └── preference_ui.py           # Streamlit sidebar widgets
│
├── recipe_engine/
│   ├── prompt_builder.py           # Structured LLM prompt builder
│   ├── groq_client.py              # Async Groq API wrapper
│   └── recipe_parser.py           # JSON response validator
│
├── ui/
│   ├── components.py               # Recipe cards + overlays
│   └── styles.css
│
├── models/
│   └── food_yolo11/
│       └── best.pt                 # Fine-tuned weights (not committed)
│
├── data/
│   ├── classes.txt                 # 30 ingredient classes
│   ├── dataset.yaml                # YOLO training config
│   ├── prepare_dataset.py          # Dataset download + merge + split pipeline
│   ├── images/                     # train / val / test splits
│   └── labels/                     # YOLO TXT annotations
│
└── training/
    ├── kaggle_train.py             # Kaggle API training pipeline (T4 GPU)
    ├── train.py
    ├── evaluate.py
    └── export.py
```

---

## Dataset & Training

### Ingredient Classes (30)

`tomato` · `onion` · `garlic` · `ginger` · `potato` · `spinach` · `paneer` · `green_chili` · `lemon` · `cauliflower` · `eggplant` · `carrot` · `bell_pepper` · `mushroom` · `broccoli` · `cucumber` · `cabbage` · `egg` · `chicken` · `apple` · `banana` · `orange` · `corn` · `green_peas` · `coriander` · `coconut` · `pumpkin` · `beetroot` · `bitter_gourd` · `french_beans`

### Dataset Sources

| Source | Images | Key Coverage |
|---|---|---|
| Roboflow: 120-class Food Ingredients | ~4,200 | paneer, spinach, bitter_gourd, coriander |
| Roboflow: Combined Vegetables & Fruits | ~42,000 | 22/30 common classes |
| Mendeley Bangladesh Vegetables | ~3,534 | beetroot, bitter_gourd, green_chili, french_beans |

**Total after merge & dedup: 36,503 images** (80% train / 10% val / 10% test)

### Training on Kaggle (Free T4 GPU)

The `training/kaggle_train.py` script handles the full pipeline automatically:

```bash
# One-time full run (~2–2.5 hrs on T4)
python3.13 training/kaggle_train.py

# Quick test (30 epochs, smaller model, ~1.5 hrs)
python3.13 training/kaggle_train.py --model yolo11s.pt --epochs 30

# Skip re-upload if dataset already on Kaggle
python3.13 training/kaggle_train.py --skip-upload

# Just download the trained model
python3.13 training/kaggle_train.py --download-only
```

**Required in `.env`:**
```env
KAGGLE_API_TOKEN=KGAT_...
KAGGLE_USERNAME=your_kaggle_username
```

### Model Size vs. Speed

| Model | Parameters | Speed (T4) | Recommended For |
|---|---|---|---|
| `yolo11n.pt` | 2.6M | ~120 FPS | CPU / low-end |
| `yolo11s.pt` | 9.4M | ~90 FPS | Fast iteration |
| **`yolo11m.pt`** | **20M** | **~60 FPS** | **Production (recommended)** |
| `yolo11l.pt` | 25M | ~40 FPS | Max accuracy |

Target metric: **mAP@0.5 > 0.75**

---

## Setup & Installation

### Prerequisites

- Python 3.13+
- Webcam
- [Groq API key](https://console.groq.com/) (free tier available)
- [Kaggle account](https://www.kaggle.com/settings) (for training)

### 1. Clone the repository

```bash
git clone https://github.com/SaiKrishnaMulukutla/SmartPantryAI.git
cd SmartPantryAI
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_api_key
ROBOFLOW_API_KEY=your_roboflow_key
KAGGLE_API_TOKEN=KGAT_your_token
KAGGLE_USERNAME=your_kaggle_username
YOLO_MODEL_PATH=models/food_yolo11/best.pt
CONFIDENCE_THRESHOLD=0.5
MAX_RECIPES=3
```

### 4. Prepare dataset

```bash
python3 data/prepare_dataset.py
```

### 5. Train the model

```bash
python3 training/kaggle_train.py
```

### 6. Add weights

Place the downloaded `best.pt` at `models/food_yolo11/best.pt`.

---

## Running the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

**Workflow:**
1. Set preferences in the left sidebar
2. Click **Start Camera**
3. Hold ingredients up to the camera — bounding boxes appear
4. Click **Get Recipes**
5. Recipe cards appear with ingredients, steps, and cook time

---

## API Reference

### `detector/yolo_detector.py`

```python
class YOLODetector:
    def __init__(self, model_path: str, confidence: float = 0.5)
    def detect(self, frame: np.ndarray) -> list[Detection]
    def draw_boxes(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray
```

### `preference_engine/schema.py`

```python
class UserPreferences(BaseModel):
    diet: Literal["veg", "non_veg", "eggetarian"]
    health: Literal["normal", "diabetic", "low_bp", "high_bp"]
    cuisine: Literal["north_indian", "south_indian", "chinese", "mediterranean", "japanese"]
    mood: Literal["party", "tired", "romantic", "quick_bite"]
    time_minutes: Literal[10, 20, 30, 40]
```

### `recipe_engine/groq_client.py`

```python
class GroqRecipeClient:
    async def get_recipes(self, prompt: str, temperature: float = 0.7) -> list[Recipe]
```

---

## Build Status

| Component | Status |
|---|---|
| Project scaffold & README | ✅ Done |
| 30-class ingredient list | ✅ Done |
| Dataset pipeline (36,503 images) | ✅ Done |
| Preference engine (schema + UI) | ✅ Done |
| Recipe prompt builder | ✅ Done |
| Kaggle training pipeline | ✅ Done |
| Detector layer (YOLOv11 wrapper) | 🔧 In Progress |
| Groq client + recipe parser | 🔧 In Progress |
| Streamlit UI (app.py) | 🔧 In Progress |
| Trained model (best.pt) | ⏳ Pending training run |

---

## Roadmap

### v1.0 — Core Pipeline *(current)*
- [x] Project scaffold and README
- [x] Dataset download + preparation pipeline
- [x] Preference Engine (5 dimensions)
- [x] Recipe prompt builder
- [x] Kaggle API training pipeline
- [ ] YOLOv11 food ingredient detection (fine-tuned model)
- [ ] OpenCV webcam integration
- [ ] Groq API integration (recipe generation)
- [ ] Streamlit UI — live feed + recipe cards

### v1.1 — Enhanced Detection
- [ ] Multi-frame ingredient aggregation
- [ ] Confidence threshold slider in UI
- [ ] OCR for packaged food labels (Tesseract)

### v1.2 — Smarter Recipes
- [ ] Calorie and macro estimation (USDA FoodData API)
- [ ] Recipe rating and feedback loop
- [ ] Save favourite recipes to local store

### v2.0 — Personalization & Deployment
- [ ] User accounts with persistent profiles (SQLite)
- [ ] Weekly meal planner
- [ ] Docker + Hugging Face Spaces deployment
- [ ] Multi-language recipe output (Hindi, Tamil, etc.)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  Built by <a href="https://github.com/SaiKrishnaMulukutla">Sai Krishna Mulukutla</a>
</div>

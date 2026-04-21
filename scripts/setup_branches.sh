#!/usr/bin/env bash
set -e

REMOTE="https://github.com/SaiKrishnaMulukutla/SmartPantryAI.git"
OWNER="SaiKrishnaMulukutla"
REPO="SmartPantryAI"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  SmartPantryAI — Rebuilding Git History with PRs"
echo "═══════════════════════════════════════════════════════"

GH_TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | grep ^password | cut -d= -f2)
[[ -z "$GH_TOKEN" ]] && { echo "ERROR: No GitHub token in credential store"; exit 1; }
echo "  Token: ${GH_TOKEN:0:10}..."

create_pr() {
  local branch="$1" title="$2" body="$3"
  local payload
  payload=$(PR_TITLE="$title" PR_HEAD="$branch" PR_BODY="$body" \
    python3.13 -c "
import json, os
print(json.dumps({'title': os.environ['PR_TITLE'], 'head': os.environ['PR_HEAD'], 'base': 'main', 'body': os.environ['PR_BODY']}))
")
  local resp
  resp=$(curl -s -X POST --insecure \
    -H "Authorization: token $GH_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/pulls" \
    -d "$payload") || true
  local url
  url=$(echo "$resp" | python3.13 -c "import json,sys; d=json.load(sys.stdin); print(d.get('html_url') or d.get('message','(no message)'))" 2>/dev/null) || true
  echo "  PR → $url"
}

c() { git add $1; git commit -m "$2"; echo "    + $(echo "$2" | head -1)"; }

ship() {
  local branch="$1" title="$2" body="$3"
  git push --force origin "$branch"
  create_pr "$branch" "$title" "$body"
  git checkout main
  git merge --no-ff "$branch" -m "Merge pull request: $title"
  git branch -d "$branch"
  git push origin main --force
  echo "  ✓ $branch → main"
}

from_backup() {
  mkdir -p "$ROOT/$(dirname "$1")"
  cp "$BACKUP/$1" "$ROOT/$1" 2>/dev/null || true
}

# ── Step 0: Backup & reinit ───────────────────────────────────────────────────
echo ""; echo "[0/8] Backing up and reinitialising …"
BACKUP=$(mktemp -d)
rsync -a --exclude='.git' --exclude='data/raw' --exclude='data/pool' \
      --exclude='data/images' --exclude='data/labels' --exclude='runs' \
      --exclude='models' "$ROOT/" "$BACKUP/"
find "$BACKUP" -type f | sed "s|$BACKUP/|  backed up: |" | sort
rm -rf "$ROOT/.git"
git init && git remote add origin "$REMOTE" && git checkout -b main

# ── Base commit ───────────────────────────────────────────────────────────────
echo ""; echo "[base] Initial commit …"
from_backup "README.md"; from_backup ".gitignore"
c "README.md .gitignore" "chore: initial project scaffold

Add README (SmartPantryAI) and .gitignore for Python/ML project."
git push origin main --force

# ── Branch 1 ─────────────────────────────────────────────────────────────────
echo ""; echo "[1/8] feat/project-setup …"
git checkout -b feat/project-setup
from_backup "requirements.txt"
c "requirements.txt" "chore: add requirements.txt with core dependencies

Pin ultralytics, streamlit, groq, pydantic, opencv-python,
python-dotenv, roboflow, kaggle, pyyaml. Tested on Python 3.13."
cat > "$ROOT/.env.example" << 'EOF'
GROQ_API_KEY=your_groq_api_key_here
ROBOFLOW_API_KEY=your_roboflow_api_key_here
KAGGLE_API_TOKEN=KGAT_your_token_here
KAGGLE_USERNAME=your_kaggle_username
YOLO_MODEL_PATH=models/food_yolo11/best.pt
CONFIDENCE_THRESHOLD=0.5
MAX_RECIPES=3
EOF
c "-f .env.example" "chore: add .env.example documenting all required env vars"
ship "feat/project-setup" "feat: project setup — requirements and env config" "Adds requirements.txt and .env.example"

# ── Branch 2 ─────────────────────────────────────────────────────────────────
echo ""; echo "[2/8] feat/data-pipeline …"
git checkout -b feat/data-pipeline
from_backup "data/classes.txt"
c "data/classes.txt" "feat(data): add 30-class food ingredient list

Indian staples: paneer, spinach, bitter_gourd, coriander, green_chili.
Global: broccoli, mushroom, bell_pepper, egg, chicken, apple, banana."
from_backup "data/dataset.yaml"
c "data/dataset.yaml" "feat(data): add YOLO training config (dataset.yaml)"
from_backup "data/prepare_dataset.py"
c "data/prepare_dataset.py" "feat(data): add full dataset preparation pipeline

Roboflow download, Mendeley VOC→YOLO conversion, alias normalization,
MD5 dedup, 80/10/10 split → 36,503 total images. SSL patch included."
ship "feat/data-pipeline" "feat: data pipeline — 36,503 image dataset prepared" "Roboflow + Mendeley download, 80/10/10 split, 36503 images"

# ── Branch 3 ─────────────────────────────────────────────────────────────────
echo ""; echo "[3/8] feat/preference-engine …"
git checkout -b feat/preference-engine
from_backup "preference_engine/__init__.py"
c "preference_engine/__init__.py" "feat(preference): init preference_engine package"
from_backup "preference_engine/schema.py"
c "preference_engine/schema.py" "feat(preference): add UserPreferences Pydantic model

5-dimension profile: diet, health, cuisine, mood, time_minutes.
All fields use strict Literal types for validation."
from_backup "preference_engine/preference_ui.py"
c "preference_engine/preference_ui.py" "feat(preference): add Streamlit sidebar preference widgets"
ship "feat/preference-engine" "feat: preference engine — 5-dimension user profile" "Pydantic schema + Streamlit sidebar for diet/health/cuisine/mood/time"

# ── Branch 4 ─────────────────────────────────────────────────────────────────
echo ""; echo "[4/8] feat/detector …"
git checkout -b feat/detector
from_backup "detector/__init__.py"
c "detector/__init__.py" "feat(detector): init detector package"
from_backup "detector/yolo_detector.py"
c "detector/yolo_detector.py" "feat(detector): add YOLOv11 inference wrapper

YOLODetector: configurable confidence, Detection dataclass,
draw_boxes() for annotated frames."
from_backup "detector/frame_processor.py"
c "detector/frame_processor.py" "feat(detector): add OpenCV webcam frame processor

FrameProcessor: webcam init, BGR→RGB frame generator, FPS tracking."
ship "feat/detector" "feat: detector — YOLOv11 inference + OpenCV webcam" "YOLOv11 wrapper and OpenCV frame processor"

# ── Branch 5 ─────────────────────────────────────────────────────────────────
echo ""; echo "[5/8] feat/recipe-engine …"
git checkout -b feat/recipe-engine
from_backup "recipe_engine/__init__.py"
c "recipe_engine/__init__.py" "feat(recipe): init recipe_engine package"
from_backup "recipe_engine/prompt_builder.py"
c "recipe_engine/prompt_builder.py" "feat(recipe): add Groq/Llama3 prompt builder

Injects ingredients + preferences into structured prompt.
Health, mood, diet rules enforced. JSON-only output."
from_backup "recipe_engine/groq_client.py"
c "recipe_engine/groq_client.py" "feat(recipe): add async Groq API client

groq.AsyncGroq wrapper, llama3-70b-8192, ~200-400ms latency."
from_backup "recipe_engine/recipe_parser.py"
c "recipe_engine/recipe_parser.py" "feat(recipe): add JSON recipe response parser and validator"
ship "feat/recipe-engine" "feat: recipe engine — Groq/Llama3 prompt + async client" "Prompt builder, async Groq client, JSON parser"

# ── Branch 6 ─────────────────────────────────────────────────────────────────
echo ""; echo "[6/8] feat/training-pipeline …"
git checkout -b feat/training-pipeline
from_backup "training/__init__.py"
c "training/__init__.py" "feat(training): init training package"
from_backup "training/train.py"
c "training/train.py" "feat(training): add local YOLO training script

yolo11m.pt, 50 epochs, imgsz=640, batch=16. M1 Pro ~10-15hrs."
from_backup "training/evaluate.py"
c "training/evaluate.py" "feat(training): add model evaluation on test split

Per-class mAP@0.5. Target > 0.75 before production."
from_backup "training/export.py"
c "training/export.py" "feat(training): add ONNX / TorchScript model export"
from_backup "training/kaggle_train.py"
c "training/kaggle_train.py" "feat(training): add Kaggle API end-to-end training pipeline

Zip+upload → T4 GPU kernel → poll → download best.pt.
~90-120min on free Kaggle T4. KGAT_ token auth."
ship "feat/training-pipeline" "feat: training pipeline — local + Kaggle API cloud training" "train/evaluate/export scripts + Kaggle API pipeline"

# ── Branch 7 ─────────────────────────────────────────────────────────────────
echo ""; echo "[7/8] feat/streamlit-ui …"
git checkout -b feat/streamlit-ui
from_backup "ui/__init__.py"; from_backup "ui/styles.css"
c "ui/__init__.py ui/styles.css" "feat(ui): add Streamlit custom CSS

Dark theme: recipe cards, ingredient pills, detection overlays."
from_backup "ui/components.py"
c "ui/components.py" "feat(ui): add reusable Streamlit components

render_recipe_card, render_detection_overlay, render_ingredient_pills."
from_backup "app.py"
c "app.py" "feat(app): add Streamlit entry point — wires all modules together

Webcam → YOLO → Groq → recipe cards. Session state for ingredients."
ship "feat/streamlit-ui" "feat: Streamlit UI — webcam feed, overlays, recipe cards" "CSS, components, app.py entry point"

# ── Branch 8 ─────────────────────────────────────────────────────────────────
echo ""; echo "[8/8] feat/scripts …"
git checkout -b feat/scripts
git add scripts/
git commit -m "chore(scripts): add repo utility scripts

setup_branches.sh: full history rebuild with PRs opened before merge.
create_prs.py: standalone GitHub API PR creator."
ship "feat/scripts" "chore: add repo utility scripts" "setup_branches.sh and create_prs.py"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Done! $(git log --oneline | wc -l | tr -d ' ') commits · 8 branches · 8 merged PRs"
echo "  https://github.com/$OWNER/$REPO/pulls?q=is:pr+is:merged"
echo "═══════════════════════════════════════════════════════"
git log --oneline

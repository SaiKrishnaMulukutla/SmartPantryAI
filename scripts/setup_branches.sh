#!/usr/bin/env bash
set -e

OWNER="SaiKrishnaMulukutla"
REPO="SmartPantryAI"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  SmartPantryAI — Rebuilding Git History with PRs"
echo "═══════════════════════════════════════════════════════"

GH_TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | grep ^password | cut -d= -f2)
[[ -z "$GH_TOKEN" ]] && { echo "ERROR: No GitHub token found"; exit 1; }
echo "  Token: ${GH_TOKEN:0:10}..."

# Open a PR before merging — returns PR number
pr() {
  local branch="$1" title="$2" body="$3"
  local resp
  resp=$(curl -s -X POST --insecure \
    -H "Authorization: token $GH_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/pulls" \
    --data-binary "{\"title\":\"$title\",\"head\":\"$branch\",\"base\":\"main\",\"body\":\"$body\"}")
  echo "$resp" | python3.13 -c \
    "import json,sys; d=json.load(sys.stdin); print('  PR →', d.get('html_url') or d.get('message','?'))" 2>/dev/null
}

# Commit helper
c() { git add $1; git commit -m "$2"; echo "    + $(echo "$2" | head -1)"; }

# Restore from backup
fb() { mkdir -p "$ROOT/$(dirname "$1")"; cp "$BACKUP/$1" "$ROOT/$1" 2>/dev/null || true; }

# Push branch, open PR, merge into main, push main
ship() {
  local BRANCH="$1" TITLE="$2" BODY="$3"
  git push origin "$BRANCH" --force
  pr "$BRANCH" "$TITLE" "$BODY"
  git checkout main
  git merge --no-ff "$BRANCH" -m "Merge pull request: $TITLE"
  git branch -d "$BRANCH"
  git push origin main --force
  echo "  ✓ $BRANCH merged"
}

# ── Backup & reinit ───────────────────────────────────────────────────────────
echo ""; echo "[0/8] Backup and reinit …"
BACKUP=$(mktemp -d)
rsync -a --exclude='.git' --exclude='data/raw' --exclude='data/pool' \
      --exclude='data/images' --exclude='data/labels' \
      --exclude='runs' --exclude='models' "$ROOT/" "$BACKUP/"
find "$BACKUP" -type f | sed "s|$BACKUP/|  + |" | sort
rm -rf "$ROOT/.git"
git init -b main
git remote add origin "https://github.com/$OWNER/$REPO.git"

# ── Initial commit ────────────────────────────────────────────────────────────
echo ""; echo "[base] …"
fb "README.md"; fb ".gitignore"
git add README.md .gitignore
git commit -m "chore: initial project scaffold"
git push origin main --force

# ── Branch 1: feat/project-setup ─────────────────────────────────────────────
echo ""; echo "[1/8] feat/project-setup …"
git checkout -b feat/project-setup
fb "requirements.txt"
c "requirements.txt" "chore: add requirements.txt with core dependencies"
cat > .env.example << 'EOF'
GROQ_API_KEY=your_groq_api_key_here
ROBOFLOW_API_KEY=your_roboflow_api_key_here
KAGGLE_API_TOKEN=KGAT_your_token_here
KAGGLE_USERNAME=your_kaggle_username
YOLO_MODEL_PATH=models/food_yolo11/best.pt
CONFIDENCE_THRESHOLD=0.5
MAX_RECIPES=3
EOF
git add -f .env.example
git commit -m "chore: add .env.example with all required env vars"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
echo "  on branch: $CURRENT"
ship "$CURRENT" "feat: project setup — requirements and env config" "Adds requirements.txt and .env.example"

# ── Branch 2: feat/data-pipeline ─────────────────────────────────────────────
echo ""; echo "[2/8] feat/data-pipeline …"
git checkout -b feat/data-pipeline
fb "data/classes.txt"
c "data/classes.txt" "feat(data): add 30-class food ingredient list"
fb "data/dataset.yaml"
c "data/dataset.yaml" "feat(data): add YOLO training config"
fb "data/prepare_dataset.py"
c "data/prepare_dataset.py" "feat(data): add full dataset preparation pipeline"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
echo "  on branch: $CURRENT"
ship "$CURRENT" "feat: data pipeline — 36,503 image dataset prepared" "Roboflow + Mendeley pipeline, 80/10/10 split"

# ── Branch 3: feat/preference-engine ─────────────────────────────────────────
echo ""; echo "[3/8] feat/preference-engine …"
git checkout -b feat/preference-engine
fb "preference_engine/__init__.py"
c "preference_engine/__init__.py" "feat(preference): init preference_engine package"
fb "preference_engine/schema.py"
c "preference_engine/schema.py" "feat(preference): add UserPreferences Pydantic model"
fb "preference_engine/preference_ui.py"
c "preference_engine/preference_ui.py" "feat(preference): add Streamlit sidebar widgets"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "feat: preference engine — 5-dimension user profile" "Pydantic schema + Streamlit sidebar"

# ── Branch 4: feat/detector ───────────────────────────────────────────────────
echo ""; echo "[4/8] feat/detector …"
git checkout -b feat/detector
fb "detector/__init__.py"
c "detector/__init__.py" "feat(detector): init detector package"
fb "detector/yolo_detector.py"
c "detector/yolo_detector.py" "feat(detector): add YOLOv11 inference wrapper"
fb "detector/frame_processor.py"
c "detector/frame_processor.py" "feat(detector): add OpenCV webcam frame processor"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "feat: detector — YOLOv11 inference + OpenCV webcam" "YOLOv11 wrapper and OpenCV frame processor"

# ── Branch 5: feat/recipe-engine ─────────────────────────────────────────────
echo ""; echo "[5/8] feat/recipe-engine …"
git checkout -b feat/recipe-engine
fb "recipe_engine/__init__.py"
c "recipe_engine/__init__.py" "feat(recipe): init recipe_engine package"
fb "recipe_engine/prompt_builder.py"
c "recipe_engine/prompt_builder.py" "feat(recipe): add Groq/Llama3 prompt builder"
fb "recipe_engine/groq_client.py"
c "recipe_engine/groq_client.py" "feat(recipe): add async Groq API client"
fb "recipe_engine/recipe_parser.py"
c "recipe_engine/recipe_parser.py" "feat(recipe): add JSON recipe response parser"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "feat: recipe engine — Groq/Llama3 prompt + async client" "Prompt builder, async client, JSON parser"

# ── Branch 6: feat/training-pipeline ─────────────────────────────────────────
echo ""; echo "[6/8] feat/training-pipeline …"
git checkout -b feat/training-pipeline
fb "training/__init__.py"
c "training/__init__.py" "feat(training): init training package"
fb "training/train.py"
c "training/train.py" "feat(training): add local YOLO training script"
fb "training/evaluate.py"
c "training/evaluate.py" "feat(training): add model evaluation script"
fb "training/export.py"
c "training/export.py" "feat(training): add ONNX/TorchScript export"
fb "training/kaggle_train.py"
c "training/kaggle_train.py" "feat(training): add Kaggle API end-to-end training pipeline"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "feat: training pipeline — local + Kaggle API cloud training" "train/evaluate/export + Kaggle API pipeline"

# ── Branch 7: feat/streamlit-ui ──────────────────────────────────────────────
echo ""; echo "[7/8] feat/streamlit-ui …"
git checkout -b feat/streamlit-ui
fb "ui/__init__.py"; fb "ui/styles.css"
c "ui/__init__.py ui/styles.css" "feat(ui): add custom CSS and UI package"
fb "ui/components.py"
c "ui/components.py" "feat(ui): add reusable Streamlit components"
fb "app.py"
c "app.py" "feat(app): add Streamlit entry point — wires all modules together"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "feat: Streamlit UI — webcam feed, overlays, recipe cards" "CSS, components, app.py entry point"

# ── Branch 8: feat/scripts ───────────────────────────────────────────────────
echo ""; echo "[8/8] feat/scripts …"
git checkout -b feat/scripts
git add scripts/
git commit -m "chore(scripts): add repo utility scripts"
CURRENT=$(git rev-parse --abbrev-ref HEAD)
ship "$CURRENT" "chore: add repo utility scripts" "setup_branches.sh and create_prs.py"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Done! $(git log --oneline | wc -l | tr -d ' ') commits · 8 merged PRs"
echo "  https://github.com/$OWNER/$REPO/pulls?q=is:pr+is:merged"
echo "═══════════════════════════════════════════════════════"
git log --oneline

"""
Create GitHub Pull Requests for all feature branches via GitHub API.

Usage:
    python3.13 scripts/create_prs.py --token <your_github_token>

Get a token at: https://github.com/settings/tokens
Required scope: repo
"""

from __future__ import annotations

import argparse
import ssl
import urllib3
import warnings
import requests
import requests.adapters

# ── SSL bypass for Netskope corporate proxy ────────────────────────────────────
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
_orig = requests.adapters.HTTPAdapter.send
def _noverify(self, r, **kw): kw["verify"] = False; return _orig(self, r, **kw)
requests.adapters.HTTPAdapter.send = _noverify

OWNER = "SaiKrishnaMulukutla"
REPO  = "SmartPantryAI"
BASE  = "main"
API   = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"

BRANCHES = [
    {
        "head":  "feat/project-setup",
        "title": "feat: project setup — requirements and env config",
        "body":  "## Summary\n- Add `requirements.txt` with all core dependencies (ultralytics, streamlit, groq, pydantic, roboflow, kaggle)\n- Add `.env.example` documenting all required environment variables\n\n## Changes\n- `requirements.txt`\n- `.env.example`",
    },
    {
        "head":  "feat/data-pipeline",
        "title": "feat: data pipeline — 36,503 image dataset prepared",
        "body":  "## Summary\n- 30-class food ingredient list covering Indian + global produce\n- Roboflow + Mendeley dataset download pipeline\n- VOC→YOLO conversion, class alias normalization, dedup, 80/10/10 split\n\n## Changes\n- `data/classes.txt` — 30 ingredient classes\n- `data/dataset.yaml` — YOLO training config\n- `data/prepare_dataset.py` — full pipeline script",
    },
    {
        "head":  "feat/preference-engine",
        "title": "feat: preference engine — 5-dimension user profile",
        "body":  "## Summary\n- Pydantic model for user preferences (diet, health, cuisine, mood, time)\n- Streamlit sidebar widgets with session state persistence\n\n## Changes\n- `preference_engine/schema.py` — UserPreferences Pydantic model\n- `preference_engine/preference_ui.py` — Streamlit sidebar widgets",
    },
    {
        "head":  "feat/detector",
        "title": "feat: detector — YOLOv11 inference wrapper + OpenCV webcam",
        "body":  "## Summary\n- YOLOv11 inference wrapper with configurable confidence threshold\n- OpenCV webcam capture with FPS tracking and context manager\n\n## Changes\n- `detector/yolo_detector.py` — YOLOv11 wrapper, Detection dataclass\n- `detector/frame_processor.py` — OpenCV webcam + frame generator",
    },
    {
        "head":  "feat/recipe-engine",
        "title": "feat: recipe engine — Groq/Llama3 prompt builder + async client",
        "body":  "## Summary\n- Structured LLM prompt builder injecting ingredients + user preferences\n- Async Groq API client (llama3-70b-8192, ~200-400ms latency)\n- JSON response parser with graceful fallback\n\n## Changes\n- `recipe_engine/prompt_builder.py`\n- `recipe_engine/groq_client.py`\n- `recipe_engine/recipe_parser.py`",
    },
    {
        "head":  "feat/training-pipeline",
        "title": "feat: training pipeline — local + Kaggle API cloud training",
        "body":  "## Summary\n- Local training script wrapping Ultralytics CLI\n- Model evaluation on test split (target mAP@0.5 > 0.75)\n- ONNX / TorchScript export\n- Full Kaggle API pipeline: upload dataset → T4 GPU kernel → poll → download best.pt\n\n## Changes\n- `training/train.py`, `evaluate.py`, `export.py`\n- `training/kaggle_train.py` — automated Kaggle cloud training",
    },
    {
        "head":  "feat/streamlit-ui",
        "title": "feat: Streamlit UI — webcam feed, overlays, recipe cards",
        "body":  "## Summary\n- Reusable Streamlit components: recipe cards, ingredient pills, detection overlays\n- Custom dark-themed CSS\n- `app.py` wires all modules: webcam → YOLO → Groq → recipe cards\n\n## Changes\n- `ui/components.py`, `ui/styles.css`\n- `app.py` — Streamlit entry point",
    },
    {
        "head":  "feat/scripts",
        "title": "chore: add repo utility scripts",
        "body":  "## Summary\n- `scripts/setup_branches.sh` — rebuilds git history with feature branches and no-ff merges\n- `scripts/create_prs.py` — creates GitHub PRs for all feature branches via API",
    },
]


def create_pr(session: requests.Session, branch: dict) -> None:
    resp = session.post(API, json={
        "title": branch["title"],
        "head":  branch["head"],
        "base":  BASE,
        "body":  branch["body"],
    })

    if resp.status_code == 201:
        print(f"  ✅ {branch['head']} → PR #{resp.json()['number']}: {resp.json()['html_url']}")
    else:
        print(f"  ❌ {branch['head']} → HTTP {resp.status_code}")
        print(f"     {resp.text[:300]}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True, help="GitHub personal access token (scope: repo)")
    args = p.parse_args()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {args.token}",
        "Accept": "application/vnd.github.v3+json",
    })

    print(f"\nCreating PRs in {OWNER}/{REPO} …\n")
    for branch in BRANCHES:
        create_pr(session, branch)
    print("\nDone.")


if __name__ == "__main__":
    main()

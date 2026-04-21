"""
Train the food ingredient YOLO model on Kaggle (free T4 GPU) via the Kaggle API.

This script handles the full pipeline:
  1. Zip and upload the prepared dataset as a Kaggle Dataset
  2. Push a training kernel (notebook) with GPU enabled
  3. Poll until training completes
  4. Download best.pt to models/food_yolo11/best.pt

Prerequisites:
  pip install kaggle
  Add to .env:
    KAGGLE_USERNAME=your_kaggle_username
    KAGGLE_KEY=your_kaggle_api_key
  Get your key at: https://www.kaggle.com/settings → API → Create New Token
  (Downloads kaggle.json — copy the username and key values into .env)

Usage:
    python training/kaggle_train.py
    python training/kaggle_train.py --epochs 80 --model yolo11l.pt
    python training/kaggle_train.py --skip-upload   # if dataset already pushed
    python training/kaggle_train.py --download-only # just fetch the model
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import ssl
import tempfile
import time
import urllib3
import warnings
import zipfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Kaggle token — must be in env BEFORE kaggle is imported ───────────────────
# kaggle/__init__.py calls api.authenticate() on import, so we pre-set
# KAGGLE_API_TOKEN here from .env so the SDK picks it up immediately.
_kaggle_token = os.getenv("KAGGLE_API_TOKEN")
if _kaggle_token:
    os.environ["KAGGLE_API_TOKEN"] = _kaggle_token
    # Ensure kaggle.json doesn't contain a stale key-only entry that triggers
    # the legacy username+key auth path instead of the new token path.
    _kaggle_creds = Path.home() / ".kaggle" / "kaggle.json"
    if _kaggle_creds.exists():
        try:
            _stored = json.loads(_kaggle_creds.read_text())
            if "username" not in _stored:
                _kaggle_creds.unlink()   # remove incomplete legacy file
        except Exception:
            pass

# ── SSL bypass for Netskope corporate proxy ────────────────────────────────────
# Patch at the HTTPAdapter level so ALL outbound requests — including those made
# by kagglesdk which calls session.send() directly — bypass SSL verification.
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import requests  # noqa: E402
import requests.adapters  # noqa: E402

_orig_adapter_send = requests.adapters.HTTPAdapter.send
def _noverify_send(self, request, **kwargs):
    kwargs["verify"] = False
    return _orig_adapter_send(self, request, **kwargs)
requests.adapters.HTTPAdapter.send = _noverify_send

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
DATA_DIR    = ROOT / "data"
MODELS_DIR  = ROOT / "models" / "food_yolo11"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Kaggle identifiers ─────────────────────────────────────────────────────────
# These are used as the Kaggle dataset/kernel slugs — lowercase, no spaces.
DATASET_TITLE = "food-ingredient-yolo-dataset"
KERNEL_TITLE  = "food-ingredient-yolo-training"


# ── Argument parsing ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLO on Kaggle via API")
    p.add_argument("--model",         default="yolo11m.pt",
                   help="Pretrained checkpoint (default: yolo11m.pt)")
    p.add_argument("--epochs",        type=int, default=50,
                   help="Training epochs (default: 50)")
    p.add_argument("--imgsz",         type=int, default=640,
                   help="Image size (default: 640)")
    p.add_argument("--batch",         type=int, default=16,
                   help="Batch size (default: 16)")
    p.add_argument("--skip-upload",   action="store_true",
                   help="Skip dataset upload (use if already pushed to Kaggle)")
    p.add_argument("--download-only", action="store_true",
                   help="Only download the latest kernel output (best.pt)")
    p.add_argument("--poll-interval", type=int, default=60,
                   help="Seconds between kernel status polls (default: 60)")
    return p.parse_args()


# ── Kaggle client setup ────────────────────────────────────────────────────────

def get_kaggle_client():
    """
    Authenticate with the Kaggle API.
    Kaggle SDK v1.6+ exposes a pre-authenticated `kaggle.api` instance —
    no need to instantiate KaggleApiExtended manually.
    """
    try:
        import kaggle  # triggers authenticate() in __init__.py
        api = kaggle.api
    except Exception as exc:
        if "kaggle" not in str(type(exc).__module__):
            raise SystemExit(f"kaggle package not found. Run: pip install kaggle\n({exc})")
        raise SystemExit(f"Kaggle auth failed: {exc}")

    username = os.getenv("KAGGLE_USERNAME") or api.get_config_value("username") or ""
    if not username:
        raise SystemExit(
            "Could not resolve Kaggle username.\n"
            "Add KAGGLE_USERNAME=your_username to .env"
        )

    print(f"  Authenticated as: {username}")
    return api, username


# ── Step 1: Zip the dataset ────────────────────────────────────────────────────

def zip_dataset(dest_dir: Path) -> Path:
    """
    Zip data/images + data/labels + data/classes.txt + data/dataset.yaml
    into a single archive for Kaggle upload.
    """
    zip_path = dest_dir / "food_ingredient_dataset.zip"
    if zip_path.exists():
        zip_path.unlink()

    sources = [
        DATA_DIR / "images",
        DATA_DIR / "labels",
        DATA_DIR / "classes.txt",
        DATA_DIR / "dataset.yaml",
    ]

    missing = [s for s in sources if not s.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing dataset files: {missing}\n"
            "Run `python3.13 data/prepare_dataset.py` first."
        )

    print(f"  Zipping dataset → {zip_path} …")
    total = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for source in sources:
            if source.is_dir():
                for f in source.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(DATA_DIR.parent))
                        total += 1
            else:
                zf.write(source, source.relative_to(DATA_DIR.parent))
                total += 1

    size_mb = zip_path.stat().st_size / 1e6
    print(f"  Zipped {total:,} files — {size_mb:.1f} MB")
    return zip_path


# ── Step 2: Upload dataset to Kaggle ──────────────────────────────────────────

def upload_dataset(api, username: str, zip_path: Path) -> str:
    """
    Create or update a Kaggle dataset from the zip file.
    Returns the full dataset ref: username/dataset-title
    """
    dataset_ref = f"{username}/{DATASET_TITLE}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy zip into the temp staging dir
        shutil.copy2(zip_path, tmp_path / zip_path.name)

        # Write dataset-metadata.json
        metadata = {
            "title":   DATASET_TITLE,
            "id":      dataset_ref,
            "licenses": [{"name": "CC0-1.0"}],
        }
        (tmp_path / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2))

        # Check if dataset already exists → update, else create
        try:
            api.dataset_list(search=DATASET_TITLE, user=username)
            print(f"  Updating existing dataset: {dataset_ref}")
            api.dataset_create_version(
                str(tmp_path),
                version_notes="Auto-updated by kaggle_train.py",
                quiet=False,
                convert_to_csv=False,
                delete_old_versions=False,
            )
        except Exception:
            print(f"  Creating new dataset: {dataset_ref}")
            api.dataset_create_new(
                str(tmp_path),
                public=False,
                quiet=False,
                convert_to_csv=False,
            )

    print(f"  Dataset ready: https://www.kaggle.com/datasets/{dataset_ref}")
    return dataset_ref


# ── Step 3: Build training kernel source ──────────────────────────────────────

def build_kernel_source(
    username: str,
    dataset_ref: str,
    model: str,
    epochs: int,
    imgsz: int,
    batch: int,
) -> dict:
    """
    Build the Kaggle kernel metadata + notebook JSON that runs YOLO training.
    """
    kernel_slug = KERNEL_TITLE

    # The notebook cells — runs inside Kaggle's container
    notebook_source = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": [
            _code_cell("# Install Ultralytics\n!pip install ultralytics -q"),
            _code_cell("import os\nprint('GPU:', os.popen('nvidia-smi --query-gpu=name --format=csv,noheader').read().strip())"),
            _code_cell(
                "# Dataset is mounted at /kaggle/input/<dataset-slug>/\n"
                "import glob, os\n"
                "dataset_root = '/kaggle/input/" + DATASET_TITLE + "'\n"
                "print('Dataset files:', len(glob.glob(dataset_root + '/**/*', recursive=True)))"
            ),
            _code_cell(
                "# Write data.yaml pointing to the Kaggle input path\n"
                "import yaml, shutil\n"
                "with open(f'{dataset_root}/data/dataset.yaml') as f:\n"
                "    cfg = yaml.safe_load(f)\n"
                "cfg['path'] = dataset_root + '/data'\n"
                "with open('/kaggle/working/data.yaml', 'w') as f:\n"
                "    yaml.dump(cfg, f)\n"
                "print('data.yaml written:')\n"
                "print(open('/kaggle/working/data.yaml').read())"
            ),
            _code_cell(
                f"# Train\n"
                f"!yolo detect train \\\n"
                f"  data=/kaggle/working/data.yaml \\\n"
                f"  model={model} \\\n"
                f"  epochs={epochs} \\\n"
                f"  imgsz={imgsz} \\\n"
                f"  batch={batch} \\\n"
                f"  name=food_yolo11 \\\n"
                f"  project=/kaggle/working/runs \\\n"
                f"  exist_ok=True"
            ),
            _code_cell(
                "# Copy best.pt to working root so it appears in kernel output\n"
                "import shutil, glob\n"
                "best = glob.glob('/kaggle/working/runs/**/best.pt', recursive=True)\n"
                "if best:\n"
                "    shutil.copy(best[0], '/kaggle/working/best.pt')\n"
                "    print('best.pt saved to /kaggle/working/best.pt')\n"
                "    print('Size:', round(os.path.getsize('/kaggle/working/best.pt')/1e6,1), 'MB')\n"
                "else:\n"
                "    print('ERROR: best.pt not found')"
            ),
            _code_cell(
                "# Print final metrics\n"
                "import glob\n"
                "results = glob.glob('/kaggle/working/runs/**/results.csv', recursive=True)\n"
                "if results:\n"
                "    import pandas as pd\n"
                "    df = pd.read_csv(results[0])\n"
                "    df.columns = df.columns.str.strip()\n"
                "    print(df[['epoch','metrics/mAP50(B)','metrics/mAP50-95(B)']].tail(5).to_string(index=False))"
            ),
        ],
    }

    kernel_metadata = {
        "id":               f"{username}/{kernel_slug}",
        "title":            KERNEL_TITLE,
        "code_file":        "kernel.ipynb",
        "language":         "python",
        "kernel_type":      "notebook",
        "is_private":       True,
        "enable_gpu":       True,
        "enable_internet":  True,
        "dataset_sources":  [dataset_ref],
        "competition_sources": [],
        "kernel_sources":   [],
    }

    return {"notebook": notebook_source, "metadata": kernel_metadata, "slug": kernel_slug}


def _code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


# ── Step 4: Push kernel to Kaggle ─────────────────────────────────────────────

def push_kernel(api, username: str, kernel_data: dict) -> str:
    """Write kernel files to a temp dir and push via Kaggle API."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Write notebook
        nb_path = tmp_path / "kernel.ipynb"
        nb_path.write_text(json.dumps(kernel_data["notebook"], indent=2))

        # Write kernel metadata
        meta_path = tmp_path / "kernel-metadata.json"
        meta_path.write_text(json.dumps(kernel_data["metadata"], indent=2))

        print(f"\n  Pushing kernel: {kernel_data['metadata']['id']}")
        api.kernels_push(str(tmp_path))

    kernel_ref = f"{username}/{kernel_data['slug']}"
    print(f"  Kernel running: https://www.kaggle.com/code/{kernel_ref}")
    return kernel_ref


# ── Step 5: Poll until kernel completes ───────────────────────────────────────

def wait_for_kernel(api, kernel_ref: str, poll_interval: int) -> bool:
    """
    Poll the kernel status every `poll_interval` seconds.
    Returns True if training succeeded, False otherwise.
    """
    print(f"\n  Polling kernel status every {poll_interval}s …")
    print("  (You can also monitor at the URL above)\n")

    username, slug = kernel_ref.split("/")
    start = time.time()

    while True:
        try:
            status_obj = api.kernel_status(username, slug)
            status     = status_obj.status
            elapsed    = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            print(f"  [{mins:02d}:{secs:02d}] Status: {status}")

            if status == "complete":
                print("\n  Training complete!")
                return True
            elif status in ("error", "cancel"):
                print(f"\n  Kernel ended with status: {status}")
                print(f"  Check logs: https://www.kaggle.com/code/{kernel_ref}")
                return False

        except Exception as exc:
            print(f"  Poll error (will retry): {exc}")

        time.sleep(poll_interval)


# ── Step 6: Download best.pt ──────────────────────────────────────────────────

def download_model(api, username: str, kernel_slug: str) -> Path:
    """Download best.pt from Kaggle kernel output to models/food_yolo11/."""
    print("\n  Downloading best.pt from Kaggle output …")

    with tempfile.TemporaryDirectory() as tmp:
        api.kernels_output(kernel_slug, path=tmp, user=username, force=True)
        best_candidates = list(Path(tmp).rglob("best.pt"))
        if not best_candidates:
            raise FileNotFoundError(
                "best.pt not found in kernel output.\n"
                f"Check the kernel logs: https://www.kaggle.com/code/{username}/{kernel_slug}"
            )
        src = best_candidates[0]
        dest = MODELS_DIR / "best.pt"
        shutil.copy2(src, dest)

    size_mb = dest.stat().st_size / 1e6
    print(f"  Saved to: {dest}  ({size_mb:.1f} MB)")
    return dest


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    print("\n" + "="*60)
    print("  Food Ingredient YOLO — Kaggle Training Pipeline")
    print("="*60)
    print(f"  Model  : {args.model}")
    print(f"  Epochs : {args.epochs}")
    print(f"  Imgsz  : {args.imgsz}")
    print(f"  Batch  : {args.batch}")
    print("="*60)

    print("\n[Auth] Connecting to Kaggle …")
    api, username = get_kaggle_client()

    if args.download_only:
        print("\n[Download] Fetching latest kernel output …")
        dest = download_model(api, username, KERNEL_TITLE)
        print(f"\nDone. Model at: {dest}")
        return

    dataset_ref = f"{username}/{DATASET_TITLE}"

    if not args.skip_upload:
        print("\n[Step 1/4] Zipping dataset …")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = zip_dataset(Path(tmp))

            print("\n[Step 2/4] Uploading to Kaggle …")
            dataset_ref = upload_dataset(api, username, zip_path)
        print("  Upload complete — waiting 30s for Kaggle to process …")
        time.sleep(30)
    else:
        print(f"\n[Step 2/4] Skipping upload — using existing dataset: {dataset_ref}")

    print("\n[Step 3/4] Building and pushing training kernel …")
    kernel_data = build_kernel_source(
        username=username,
        dataset_ref=dataset_ref,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
    )
    kernel_ref = push_kernel(api, username, kernel_data)

    print("\n[Step 4/4] Waiting for training to complete …")
    print(f"  Estimated time: ~{args.epochs * 2}–{args.epochs * 3} minutes on T4 GPU")
    success = wait_for_kernel(api, kernel_ref, args.poll_interval)

    if success:
        dest = download_model(api, username, KERNEL_TITLE)
        print(f"\n{'='*60}")
        print("  Training complete!")
        print(f"  Model saved to: {dest}")
        print(f"  Run the app:    streamlit run app.py")
        print(f"{'='*60}\n")
    else:
        print("\nTraining failed. Check the Kaggle kernel logs for details.")
        print(f"  https://www.kaggle.com/code/{kernel_ref}")


if __name__ == "__main__":
    main()

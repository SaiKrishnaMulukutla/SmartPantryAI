"""
Train a YOLO model on Kaggle (free T4 GPU) via the Kaggle API.

Pipeline:
  1. Zip and upload the prepared dataset as a Kaggle Dataset
  2. Push a training kernel (notebook) with GPU enabled
  3. Poll until training completes
  4. Download best.pt to models/food_yolo11/best.pt

Usage:
    python training/kaggle_train.py
    python training/kaggle_train.py --epochs 80 --model yolo11l.pt
    python training/kaggle_train.py --skip-upload
    python training/kaggle_train.py --download-only
    python training/kaggle_train.py --download-only --kernel-ref owner/my-kernel

Prerequisites:
    pip install kaggle python-dotenv
    Set KAGGLE_API_TOKEN and KAGGLE_USERNAME in .env
    (Token format: KGAT_... from https://www.kaggle.com/settings → API)
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

# ── Kaggle token must be in env BEFORE kaggle is imported ─────────────────────
_kaggle_token = os.getenv("KAGGLE_API_TOKEN", "")
if _kaggle_token:
    os.environ["KAGGLE_API_TOKEN"] = _kaggle_token

# ── SSL: Python 3.13 enforces RFC 5280 keyUsage on CA certs — Netskope's cert ─
# lacks this extension so even REQUESTS_CA_BUNDLE=certs.pem fails. Bypass at the
# HTTPAdapter.send level (kagglesdk calls session.send() directly, not request()).
import requests.adapters  # noqa: E402
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
_orig_send = requests.adapters.HTTPAdapter.send
def _noverify(self, req, **kw): kw["verify"] = False; return _orig_send(self, req, **kw)
requests.adapters.HTTPAdapter.send = _noverify

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _slugify(text: str) -> str:
    """Lowercase, replace spaces/underscores with hyphens, strip non-alphanum."""
    text = text.lower().strip()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    return text.strip("-")


# ── Argument parsing ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLO on Kaggle via API")
    p.add_argument("--model", default="yolo11m.pt",
                   help="Pretrained checkpoint (default: yolo11m.pt)")
    p.add_argument("--epochs", type=int, default=50,
                   help="Training epochs (default: 50)")
    p.add_argument("--imgsz", type=int, default=640,
                   help="Image size (default: 640)")
    p.add_argument("--batch", type=int, default=16,
                   help="Batch size (default: 16)")
    p.add_argument("--dataset-title", default="food-ingredient-yolo-dataset",
                   help="Kaggle dataset title/slug")
    p.add_argument("--kernel-title", default="food-ingredient-yolo-training",
                   help="Kaggle kernel title/slug")
    p.add_argument("--output-dir", default=str(ROOT / "models" / "food_yolo11"),
                   help="Local directory to save best.pt")
    p.add_argument("--skip-upload", action="store_true",
                   help="Skip dataset upload (dataset already on Kaggle)")
    p.add_argument("--download-only", action="store_true",
                   help="Skip training — only download latest kernel output")
    p.add_argument("--status", action="store_true",
                   help="Print current kernel status and exit")
    p.add_argument("--kernel-ref", default="",
                   help="Override kernel ref for --download-only / --status (owner/slug)")
    p.add_argument("--poll-interval", type=int, default=60,
                   help="Seconds between kernel status polls (default: 60)")
    return p.parse_args()


# ── Kaggle auth ────────────────────────────────────────────────────────────────

def get_kaggle_client(username_override: str = ""):
    """
    Authenticate with the Kaggle API and return (api, username, resolved_token).
    Kaggle SDK v1.6+ exposes a pre-authenticated `kaggle.api` singleton.
    """
    try:
        import kaggle  # triggers authenticate() in __init__.py
        api = kaggle.api
    except ImportError:
        raise SystemExit("kaggle package not found — run: pip install kaggle")
    except Exception as exc:
        raise SystemExit(f"Kaggle auth failed: {exc}")

    username = (
        username_override
        or os.getenv("KAGGLE_USERNAME", "")
        or _try_get_config(api, "username")
    )
    if not username:
        raise SystemExit(
            "Cannot resolve Kaggle username.\n"
            "Add KAGGLE_USERNAME=your_username to .env"
        )

    print(f"  Authenticated as: {username}")
    return api, username


def _try_get_config(api, key: str) -> str:
    try:
        return api.get_config_value(key) or ""
    except Exception:
        return ""


# ── Step 1: Zip the dataset ────────────────────────────────────────────────────

def zip_dataset(dest_dir: Path) -> Path:
    """Zip data/{images,labels,classes.txt,dataset.yaml} for Kaggle upload."""
    zip_path = dest_dir / "dataset.zip"
    zip_path.unlink(missing_ok=True)

    sources = [
        DATA_DIR / "images",
        DATA_DIR / "labels",
        DATA_DIR / "classes.txt",
        DATA_DIR / "dataset.yaml",
    ]
    missing = [s for s in sources if not s.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing dataset files: {[str(m) for m in missing]}\n"
            "Run `python data/prepare_dataset.py` first."
        )

    print(f"  Zipping dataset → {zip_path} …")
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for source in sources:
            if source.is_dir():
                for f in sorted(source.rglob("*")):
                    if f.is_file():
                        zf.write(f, f.relative_to(DATA_DIR.parent))
                        count += 1
            else:
                zf.write(source, source.relative_to(DATA_DIR.parent))
                count += 1

    size_mb = zip_path.stat().st_size / 1e6
    print(f"  Zipped {count:,} files — {size_mb:.1f} MB")
    return zip_path


# ── Step 2: Upload dataset to Kaggle ──────────────────────────────────────────

def _dataset_exists(api, username: str, dataset_slug: str) -> bool:
    """Return True if the dataset already exists on Kaggle."""
    try:
        results = api.datasets_list(search=dataset_slug, user=username)
        for ds in results:
            ref = getattr(ds, "ref", "") or ""
            if ref == f"{username}/{dataset_slug}":
                return True
    except Exception:
        pass
    return False


def upload_dataset(api, username: str, zip_path: Path, dataset_title: str) -> str:
    """Create or update a Kaggle dataset. Returns the full ref: owner/slug."""
    dataset_slug = _slugify(dataset_title)
    dataset_ref = f"{username}/{dataset_slug}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copy2(zip_path, tmp_path / zip_path.name)

        metadata = {
            "title": dataset_title,
            "id": dataset_ref,
            "licenses": [{"name": "CC0-1.0"}],
        }
        (tmp_path / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2))

        if _dataset_exists(api, username, dataset_slug):
            print(f"  Updating existing dataset: {dataset_ref}")
            api.dataset_create_version(
                str(tmp_path),
                version_notes="Auto-updated by kaggle_train.py",
                quiet=False,
                convert_to_csv=False,
                delete_old_versions=False,
            )
        else:
            print(f"  Creating new dataset: {dataset_ref}")
            api.dataset_create_new(
                str(tmp_path),
                public=False,
                quiet=False,
                convert_to_csv=False,
            )

    print(f"  Dataset ready: https://www.kaggle.com/datasets/{dataset_ref}")
    return dataset_ref


# ── Step 3: Build training kernel ─────────────────────────────────────────────

def _code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def build_kernel_source(
    username: str,
    dataset_ref: str,
    kernel_title: str,
    model: str,
    epochs: int,
    imgsz: int,
    batch: int,
) -> dict:
    """Build Kaggle kernel metadata + notebook that runs YOLO training."""
    kernel_slug = _slugify(kernel_title)
    dataset_slug = dataset_ref.split("/")[-1]

    # Discover dataset root dynamically — don't hardcode the slug
    discover_dataset = (
        "import glob, os\n"
        "candidates = glob.glob('/kaggle/input/*/data/dataset.yaml')\n"
        "if not candidates:\n"
        "    raise FileNotFoundError('dataset.yaml not found in /kaggle/input')\n"
        "dataset_root = os.path.dirname(os.path.dirname(candidates[0]))\n"
        "print('Dataset root:', dataset_root)\n"
        "print('Files:', len(glob.glob(dataset_root + '/**/*', recursive=True)))"
    )

    patch_yaml = (
        "import yaml\n"
        "with open(f'{dataset_root}/data/dataset.yaml') as f:\n"
        "    cfg = yaml.safe_load(f)\n"
        "cfg['path'] = dataset_root + '/data'\n"
        "with open('/kaggle/working/data.yaml', 'w') as f:\n"
        "    yaml.dump(cfg, f)\n"
        "print('data.yaml written:')\n"
        "print(open('/kaggle/working/data.yaml').read())"
    )

    copy_best = (
        "import shutil, glob, os\n"
        "matches = glob.glob('/kaggle/working/runs/**/best.pt', recursive=True)\n"
        "if matches:\n"
        "    shutil.copy(matches[0], '/kaggle/working/best.pt')\n"
        "    size = os.path.getsize('/kaggle/working/best.pt') / 1e6\n"
        "    print(f'best.pt → /kaggle/working/best.pt  ({size:.1f} MB)')\n"
        "else:\n"
        "    print('ERROR: best.pt not found in runs/')"
    )

    print_metrics = (
        "import glob, pandas as pd\n"
        "results = glob.glob('/kaggle/working/runs/**/results.csv', recursive=True)\n"
        "if results:\n"
        "    df = pd.read_csv(results[0])\n"
        "    df.columns = df.columns.str.strip()\n"
        "    cols = [c for c in ['epoch','metrics/mAP50(B)','metrics/mAP50-95(B)'] if c in df.columns]\n"
        "    print(df[cols].tail(5).to_string(index=False))\n"
        "else:\n"
        "    print('No results.csv found')"
    )

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": [
            _code_cell(
                "# Cell 1 — GPU check (select T4 in Settings before running)\n"
                "import torch, os\n"
                "gpu = os.popen('nvidia-smi --query-gpu=name --format=csv,noheader').read().strip()\n"
                "print(f'GPU     : {gpu}')\n"
                "print(f'PyTorch : {torch.__version__}')\n"
                "print(f'CUDA    : {torch.version.cuda}')\n"
                "assert torch.cuda.is_available(), 'No GPU — change accelerator to T4 in Settings'"
            ),
            _code_cell(
                "# Cell 2 — install ultralytics (do NOT install torch — use Kaggle pre-installed)\n"
                "!pip install ultralytics -q"
            ),
            _code_cell(discover_dataset),
            _code_cell(patch_yaml),
            _code_cell(
                f"# Cell 5 — train\n"
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
            _code_cell(copy_best),
            _code_cell(print_metrics),
        ],
    }

    kernel_metadata = {
        "id": f"{username}/{kernel_slug}",
        "title": kernel_title,
        "code_file": "kernel.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [dataset_ref],
        "competition_sources": [],
        "kernel_sources": [],
    }

    return {"notebook": notebook, "metadata": kernel_metadata, "slug": kernel_slug}


# ── Step 4: Push kernel ────────────────────────────────────────────────────────

def push_kernel(api, username: str, kernel_data: dict) -> str:
    """Write kernel files to a temp dir and push via Kaggle API. Returns kernel ref."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "kernel.ipynb").write_text(json.dumps(kernel_data["notebook"], indent=2))
        (tmp_path / "kernel-metadata.json").write_text(json.dumps(kernel_data["metadata"], indent=2))

        kernel_ref = kernel_data["metadata"]["id"]
        print(f"  Pushing kernel: {kernel_ref}")
        api.kernels_push(str(tmp_path))

    url = f"https://www.kaggle.com/code/{kernel_ref}"
    print(f"  Kernel URL: {url}")
    return kernel_ref


# ── Step 5: Poll kernel status ────────────────────────────────────────────────

def wait_for_kernel(api, kernel_ref: str, poll_interval: int) -> bool:
    """Poll until kernel completes. Returns True on success."""
    print(f"\n  Polling every {poll_interval}s — monitor at https://www.kaggle.com/code/{kernel_ref}\n")
    start = time.time()

    while True:
        try:
            status_obj = api.kernels_status(kernel_ref)
            status_str = str(getattr(status_obj, "status", status_obj)).upper()
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            print(f"  [{mins:02d}:{secs:02d}] {status_str}")

            if "COMPLETE" in status_str:
                print("  Training complete!")
                return True
            if any(s in status_str for s in ("ERROR", "CANCEL", "FAIL")):
                print(f"  Kernel ended: {status_str}")
                return False

        except Exception as exc:
            print(f"  Poll error (will retry): {exc}")

        time.sleep(poll_interval)


# ── Step 6: Download best.pt ──────────────────────────────────────────────────

def _cli_download(kernel_ref: str, dest_dir: Path) -> None:
    """Use the kaggle CLI binary as a fallback (handles large output files better)."""
    import subprocess
    kaggle_bin = shutil.which("kaggle")
    if not kaggle_bin:
        raise FileNotFoundError("kaggle CLI not found — run: pip install kaggle")
    cmd = [kaggle_bin, "kernels", "output", kernel_ref, "-p", str(dest_dir)]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"kaggle CLI failed:\n{result.stderr}")
    print(result.stdout.strip())


def download_model(api, kernel_ref: str, output_dir: Path) -> Path:
    """
    Download kernel output to output_dir.
    Handles both flat files and zipped output from Kaggle.
    """
    print(f"\n  Downloading output from: {kernel_ref}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Try SDK first; fall back to CLI (handles large files better)
        try:
            api.kernels_output(kernel_ref, path=str(tmp_path), force=True)
        except Exception as exc:
            print(f"  SDK download failed ({exc}), trying CLI fallback …")
            _cli_download(kernel_ref, tmp_path)

        # Kaggle sometimes delivers a zip — unpack it
        for zf in list(tmp_path.glob("*.zip")):
            print(f"  Unpacking {zf.name} …")
            with zipfile.ZipFile(zf) as z:
                z.extractall(tmp_path)
            zf.unlink()

        candidates = list(tmp_path.rglob("best.pt"))
        if not candidates:
            all_files = sorted(
                str(f.relative_to(tmp_path)) for f in tmp_path.rglob("*") if f.is_file()
            )
            raise FileNotFoundError(
                f"best.pt not found in kernel output.\n"
                f"Files present: {all_files}\n\n"
                f"Training likely did not complete. Options:\n"
                f"  1. Check kernel logs:  https://www.kaggle.com/code/{kernel_ref}\n"
                f"  2. Re-run training:    python training/kaggle_train.py --skip-upload\n"
                f"  3. Check status:       python training/kaggle_train.py --status"
            )

        src = candidates[0]
        dest = output_dir / "best.pt"
        shutil.copy2(src, dest)

    size_mb = dest.stat().st_size / 1e6
    print(f"  Saved: {dest}  ({size_mb:.1f} MB)")
    return dest


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    print("\n" + "=" * 60)
    print("  Food Ingredient YOLO — Kaggle Training Pipeline")
    print("=" * 60)

    print("\n[Auth] Connecting to Kaggle …")
    api, username = get_kaggle_client()

    dataset_slug = _slugify(args.dataset_title)
    kernel_slug = _slugify(args.kernel_title)
    dataset_ref = f"{username}/{dataset_slug}"
    kernel_ref = args.kernel_ref or f"{username}/{kernel_slug}"

    if args.status:
        print(f"\n[Status] Checking kernel: {kernel_ref}")
        try:
            status_obj = api.kernels_status(kernel_ref)
            status_str = str(getattr(status_obj, "status", status_obj))
            print(f"  Status : {status_str}")
            print(f"  URL    : https://www.kaggle.com/code/{kernel_ref}")
        except Exception as exc:
            print(f"  Error fetching status: {exc}")
        return

    if args.download_only:
        print(f"\n[Download] Waiting for kernel to finish: {kernel_ref}")
        success = wait_for_kernel(api, kernel_ref, args.poll_interval)
        if not success:
            print("Kernel did not complete successfully.")
            return
        dest = download_model(api, kernel_ref, output_dir)
        print(f"\nDone. Model at: {dest}")
        return

    print(f"  Model   : {args.model}")
    print(f"  Epochs  : {args.epochs}  |  Imgsz: {args.imgsz}  |  Batch: {args.batch}")
    print(f"  Dataset : {dataset_ref}")
    print(f"  Kernel  : {kernel_ref}")
    print("=" * 60)

    if not args.skip_upload:
        print("\n[1/4] Zipping dataset …")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = zip_dataset(Path(tmp))
            print("\n[2/4] Uploading to Kaggle …")
            dataset_ref = upload_dataset(api, username, zip_path, args.dataset_title)
        print("  Waiting 30s for Kaggle to process the upload …")
        time.sleep(30)
    else:
        print(f"\n[2/4] Skipping upload — using: {dataset_ref}")

    print("\n[3/4] Building and pushing training kernel …")
    kernel_data = build_kernel_source(
        username=username,
        dataset_ref=dataset_ref,
        kernel_title=args.kernel_title,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
    )
    kernel_ref = push_kernel(api, username, kernel_data)

    print(f"\n[4/4] Waiting for training (~{args.epochs * 2}–{args.epochs * 3} min on T4) …")
    success = wait_for_kernel(api, kernel_ref, args.poll_interval)

    if success:
        dest = download_model(api, kernel_ref, output_dir)
        print(f"\n{'=' * 60}")
        print(f"  Model saved: {dest}")
        print(f"  Run the app: streamlit run app.py")
        print(f"{'=' * 60}\n")
    else:
        print(f"\n  Check logs: https://www.kaggle.com/code/{kernel_ref}")


if __name__ == "__main__":
    main()

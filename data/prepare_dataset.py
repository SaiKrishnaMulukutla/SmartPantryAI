"""
Dataset preparation pipeline for the AI Recipe Ingredient Detector.

Steps executed in order:
  1. Download Roboflow datasets (requires ROBOFLOW_API_KEY in .env)
  2. Download Mendeley Bangladesh Vegetable dataset (manual fallback with instructions)
  3. Convert Pascal VOC XML → YOLO TXT (Mendeley)
  4. Normalize class name aliases across all datasets
  5. Merge all sources into a single flat pool
  6. De-duplicate images by filename hash
  7. Split into train / val / test (80 / 10 / 10)
  8. Rewrite data/dataset.yaml with confirmed classes
  9. Print coverage report

Usage:
    python data/prepare_dataset.py

    # Skip a source if already downloaded
    python data/prepare_dataset.py --skip-roboflow1
    python data/prepare_dataset.py --skip-mendeley

    # Custom split ratios
    python data/prepare_dataset.py --val-ratio 0.1 --test-ratio 0.1
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import shutil
import ssl
import urllib3
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── SSL bypass for corporate / proxy networks ──────────────────────────────────
# Required on networks that use SSL inspection (e.g. corporate proxies).
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

import requests  # noqa: E402 — must come after ssl patch
_orig_request = requests.Session.request
def _unverified_request(self, method, url, **kwargs):
    kwargs.setdefault("verify", False)
    return _orig_request(self, method, url, **kwargs)
requests.Session.request = _unverified_request

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # downloaded zips / extracted sources land here
POOL_DIR = DATA_DIR / "pool"        # merged flat pool (images + labels)
FINAL_DIR = DATA_DIR / "images"     # final train/val/test split output

# ── Class definitions ─────────────────────────────────────────────────────────
TARGET_CLASSES: list[str] = [
    "tomato", "onion", "garlic", "ginger", "potato",
    "spinach", "paneer", "green_chili", "lemon", "cauliflower",
    "eggplant", "carrot", "bell_pepper", "mushroom", "broccoli",
    "cucumber", "cabbage", "egg", "chicken", "apple",
    "banana", "orange", "corn", "green_peas", "coriander",
    "coconut", "pumpkin", "beetroot", "bitter_gourd", "french_beans",
]

# Aliases: map raw dataset class names → our canonical TARGET_CLASSES name.
# Keys are lowercased for case-insensitive matching.
CLASS_ALIASES: dict[str, str] = {
    # eggplant
    "brinjal": "eggplant", "baingan": "eggplant", "aubergine": "eggplant",
    "bringal": "eggplant",
    # bell_pepper
    "capsicum": "bell_pepper", "shimla mirch": "bell_pepper",
    "shimla_mirch": "bell_pepper", "pepper": "bell_pepper",
    # spinach
    "palak": "spinach", "palungo": "spinach",
    # bitter_gourd
    "karela": "bitter_gourd", "bitter gourd": "bitter_gourd",
    "bittergourd": "bitter_gourd",
    # coriander
    "dhania": "coriander", "cilantro": "coriander",
    "coriander leaves": "coriander", "coriander_leaves": "coriander",
    # green_chili
    "chilli": "green_chili", "chili": "green_chili",
    "hot pepper": "green_chili", "hot_pepper": "green_chili",
    "green chili": "green_chili", "green chilli": "green_chili",
    # french_beans
    "green beans": "french_beans", "green_beans": "french_beans",
    "green bean": "french_beans", "beans": "french_beans",
    "string bean": "french_beans", "string beans": "french_beans",
    # green_peas
    "pea": "green_peas", "peas": "green_peas",
    "green peas": "green_peas",
    # chicken
    "hen": "chicken",
    # lemon
    "lime": "lemon",
}

# Roboflow dataset IDs (workspace/project/version)
ROBOFLOW_DATASETS = [
    {
        "id": "food-recipe-ingredient-images-0gnku/food-ingredients-dataset/1",
        "name": "food_ingredients_120cls",
        "desc": "120-class food ingredients (paneer, spinach, bitter_gourd, etc.)",
    },
    {
        "id": "yolo-jpkho/combined-vegetables-fruits/1",
        "name": "combined_veg_fruits",
        "desc": "Combined Vegetables & Fruits (~42,000 images, 47 classes)",
    },
]

# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare food ingredient detection dataset")
    p.add_argument("--skip-roboflow", action="store_true",
                   help="Skip Roboflow downloads (use if already downloaded)")
    p.add_argument("--skip-mendeley", action="store_true",
                   help="Skip Mendeley download step")
    p.add_argument("--val-ratio", type=float, default=0.1,
                   help="Fraction of data for validation (default: 0.1)")
    p.add_argument("--test-ratio", type=float, default=0.1,
                   help="Fraction of data for test (default: 0.1)")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for reproducible splits (default: 42)")
    return p.parse_args()


# ── Step 1: Download from Roboflow ────────────────────────────────────────────

def download_roboflow(dest: Path) -> list[Path]:
    """
    Download each Roboflow dataset via the roboflow Python SDK.
    Returns list of extracted dataset root directories.
    """
    try:
        import roboflow
    except ImportError:
        raise SystemExit(
            "roboflow package not found.\n"
            "Install it with: pip install roboflow"
        )

    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        raise SystemExit(
            "ROBOFLOW_API_KEY not found in environment.\n"
            "1. Sign up at https://roboflow.com (free)\n"
            "2. Get your API key from https://app.roboflow.com/settings/api\n"
            "3. Add to your .env file:  ROBOFLOW_API_KEY=your_key_here"
        )

    rf = roboflow.Roboflow(api_key=api_key)
    downloaded: list[Path] = []

    for ds in ROBOFLOW_DATASETS:
        print(f"\n[Roboflow] Downloading: {ds['desc']}")
        workspace_slug, project_slug, version_str = ds["id"].split("/")
        project = rf.workspace(workspace_slug).project(project_slug)
        version = project.version(int(version_str))

        # Let Roboflow create the directory itself — pre-creating it causes
        # overwrite=False to silently skip the download.
        ds_dir = dest / ds["name"]
        if ds_dir.exists():
            shutil.rmtree(ds_dir)  # remove empty/stale dir so SDK downloads fresh

        result = version.download("yolov8", location=str(ds_dir), overwrite=True)

        # Roboflow SDK downloads into a subfolder named {project}-{version}
        # inside `location`. Find the actual root with data.yaml.
        actual_dir = ds_dir
        yaml_matches = list(ds_dir.rglob("data.yaml")) if ds_dir.exists() else []
        if yaml_matches:
            actual_dir = yaml_matches[0].parent

        downloaded.append(actual_dir)
        print(f"  Saved to: {actual_dir}")

    return downloaded


# ── Step 2: Mendeley dataset ──────────────────────────────────────────────────

def prepare_mendeley(dest: Path) -> Path | None:
    """
    Check if Mendeley dataset is manually placed; print instructions if not.
    The Mendeley dataset must be downloaded manually from:
    https://data.mendeley.com/datasets/gnc4s3z2mf/3

    Expected placement: data/raw/mendeley_vegetables.zip
    OR the extracted folder:  data/raw/mendeley_vegetables/
    """
    mendeley_dir = dest / "mendeley_vegetables"
    zip_path = dest / "mendeley_vegetables.zip"

    if mendeley_dir.exists() and any(mendeley_dir.rglob("*.jpg")):
        print(f"[Mendeley] Found existing dataset at {mendeley_dir}")
        return mendeley_dir

    if zip_path.exists():
        print(f"[Mendeley] Extracting {zip_path} …")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(mendeley_dir)
        print(f"  Extracted to: {mendeley_dir}")
        return mendeley_dir

    print("\n" + "="*60)
    print("  [Mendeley] Manual download required")
    print("="*60)
    print("  This dataset cannot be downloaded automatically.")
    print("  It provides critical coverage for:")
    print("    beetroot, bitter_gourd, coriander, green_chili,")
    print("    french_beans, lemon, cauliflower, eggplant")
    print()
    print("  Steps:")
    print("  1. Go to: https://data.mendeley.com/datasets/gnc4s3z2mf/3")
    print("  2. Click 'Download All' (3,534 images, ~300MB)")
    print("  3. Place the zip file at:")
    print(f"     {zip_path}")
    print("  4. Re-run this script — extraction is automatic.")
    print("="*60 + "\n")
    return None


# ── Step 3: VOC XML → YOLO TXT conversion ────────────────────────────────────

def convert_voc_to_yolo(src_dir: Path, out_dir: Path, class_list: list[str]) -> int:
    """
    Convert Pascal VOC XML annotations to YOLO TXT format.
    Returns number of converted annotation files.
    """
    xml_files = list(src_dir.rglob("*.xml"))
    if not xml_files:
        print(f"  No XML files found in {src_dir}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    converted = 0

    for xml_path in xml_files:
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            size = root.find("size")
            img_w = int(size.find("width").text)
            img_h = int(size.find("height").text)

            if img_w == 0 or img_h == 0:
                continue

            lines: list[str] = []
            for obj in root.findall("object"):
                raw_name = obj.find("name").text.strip().lower()
                canonical = normalize_class(raw_name, class_list)
                if canonical is None:
                    continue

                cls_idx = class_list.index(canonical)
                bndbox = obj.find("bndbox")
                xmin = float(bndbox.find("xmin").text)
                ymin = float(bndbox.find("ymin").text)
                xmax = float(bndbox.find("xmax").text)
                ymax = float(bndbox.find("ymax").text)

                x_center = (xmin + xmax) / 2 / img_w
                y_center = (ymin + ymax) / 2 / img_h
                width    = (xmax - xmin) / img_w
                height   = (ymax - ymin) / img_h

                lines.append(f"{cls_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

            if lines:
                label_file = out_dir / (xml_path.stem + ".txt")
                label_file.write_text("\n".join(lines))
                converted += 1

        except Exception as exc:
            print(f"  Warning: skipping {xml_path.name} — {exc}")

    return converted


# ── Step 4: Normalize class names ─────────────────────────────────────────────

def normalize_class(raw_name: str, class_list: list[str]) -> str | None:
    """
    Map a raw class name → canonical TARGET_CLASS name.
    Returns None if the class is not relevant to our 30-class set.
    """
    name = raw_name.strip().lower()

    # Direct match
    if name in class_list:
        return name

    # Alias match
    if name in CLASS_ALIASES:
        alias = CLASS_ALIASES[name]
        if alias in class_list:
            return alias

    # Partial match (e.g. "fresh tomato" → "tomato")
    for target in class_list:
        if target in name or name in target:
            return target

    return None  # not in our target set


def remap_yolo_labels(label_dir: Path, class_map: dict[str, int]) -> int:
    """
    Re-index YOLO label files using a provided {class_name: new_index} mapping.
    Reads existing files, remaps class IDs using a name lookup file or inline map.
    Returns count of remapped files.
    """
    remapped = 0
    label_files = list(label_dir.rglob("*.txt"))

    for lf in label_files:
        lines = lf.read_text().strip().splitlines()
        new_lines: list[str] = []
        changed = False

        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            old_idx = int(parts[0])
            # We don't know old class name here — handled during merge
            new_lines.append(line)

        if new_lines:
            lf.write_text("\n".join(new_lines))

    return remapped


# ── Step 5: Merge all sources into flat pool ──────────────────────────────────

def merge_into_pool(source_dirs: list[Path], pool_dir: Path) -> None:
    """
    Walk each source directory, find image+label pairs, normalize class IDs,
    and copy into the flat pool directory.

    Expected Roboflow export structure:
        <dataset>/
            train/images/*.jpg
            train/labels/*.txt
            valid/images/*.jpg
            valid/labels/*.txt
            data.yaml (contains class names list)

    Expected Mendeley structure (after VOC conversion):
        <dataset>/
            images/*.jpg
            labels_yolo/*.txt
    """
    pool_img_dir = pool_dir / "images"
    pool_lbl_dir = pool_dir / "labels"
    pool_img_dir.mkdir(parents=True, exist_ok=True)
    pool_lbl_dir.mkdir(parents=True, exist_ok=True)

    total_copied = 0

    for src in source_dirs:
        if not src.exists():
            print(f"  Skipping missing source: {src}")
            continue

        # Load class names from data.yaml if available
        src_classes = _load_classes_from_yaml(src)
        print(f"\n[Merge] Processing: {src.name} ({len(src_classes)} classes found)")

        # Find all image files
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        images = [
            p for p in src.rglob("*")
            if p.suffix.lower() in image_extensions
            and "/labels" not in str(p)
        ]

        copied = 0
        for img_path in images:
            # Find corresponding label file
            label_path = _find_label(img_path)
            if label_path is None or not label_path.exists():
                continue

            # Parse and remap label file
            remapped_lines = _remap_label_file(label_path, src_classes)
            if not remapped_lines:
                continue

            # De-duplicate by content hash
            img_hash = _file_hash(img_path)
            dest_img = pool_img_dir / f"{img_hash}{img_path.suffix.lower()}"
            dest_lbl = pool_lbl_dir / f"{img_hash}.txt"

            if not dest_img.exists():
                shutil.copy2(img_path, dest_img)
                dest_lbl.write_text("\n".join(remapped_lines))
                copied += 1

        total_copied += copied
        print(f"  Added {copied} image-label pairs")

    print(f"\n[Merge] Total pool size: {total_copied} images")


def _load_classes_from_yaml(dataset_dir: Path) -> list[str]:
    """Load class names from Roboflow-exported data.yaml."""
    yaml_path = dataset_dir / "data.yaml"
    if not yaml_path.exists():
        # Try classes.txt
        classes_txt = dataset_dir / "classes.txt"
        if classes_txt.exists():
            return [l.strip() for l in classes_txt.read_text().splitlines() if l.strip()]
        return []

    import yaml
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return data.get("names", [])


def _find_label(img_path: Path) -> Path | None:
    """Locate the YOLO label .txt file for a given image path."""
    # Roboflow: .../images/... → .../labels/...
    label_path = Path(str(img_path).replace("/images/", "/labels/")).with_suffix(".txt")
    if label_path.exists():
        return label_path
    # Mendeley / flat: same directory, .txt extension
    flat = img_path.with_suffix(".txt")
    if flat.exists():
        return flat
    # labels_yolo sibling directory
    sibling = img_path.parent.parent / "labels_yolo" / img_path.with_suffix(".txt").name
    if sibling.exists():
        return sibling
    return None


def _remap_label_file(label_path: Path, src_classes: list[str]) -> list[str]:
    """
    Read a YOLO label file, remap class indices to TARGET_CLASSES indices.
    Drops lines for classes not in our target set.
    """
    lines = label_path.read_text().strip().splitlines()
    remapped: list[str] = []

    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            continue
        old_idx = int(parts[0])
        if old_idx >= len(src_classes):
            continue

        raw_name = src_classes[old_idx].lower()
        canonical = normalize_class(raw_name, TARGET_CLASSES)
        if canonical is None:
            continue

        new_idx = TARGET_CLASSES.index(canonical)
        remapped.append(f"{new_idx} {' '.join(parts[1:])}")

    return remapped


def _file_hash(path: Path) -> str:
    """MD5 hash of first 8KB of file for fast de-duplication."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read(8192))
    return h.hexdigest()


# ── Step 6: Train / Val / Test split ─────────────────────────────────────────

def split_dataset(
    pool_dir: Path,
    out_dir: Path,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> dict[str, int]:
    """
    Split the flat pool into train/val/test and write to:
        data/images/train/ + data/labels/train/
        data/images/val/   + data/labels/val/
        data/images/test/  + data/labels/test/
    """
    pool_images = sorted((pool_dir / "images").glob("*"))
    pool_labels = pool_dir / "labels"

    random.seed(seed)
    random.shuffle(pool_images)

    n = len(pool_images)
    n_test = int(n * test_ratio)
    n_val  = int(n * val_ratio)
    n_train = n - n_test - n_val

    splits = {
        "train": pool_images[:n_train],
        "val":   pool_images[n_train : n_train + n_val],
        "test":  pool_images[n_train + n_val :],
    }

    counts: dict[str, int] = {}
    for split_name, images in splits.items():
        img_out = out_dir / split_name
        lbl_out = DATA_DIR / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path in images:
            label_path = pool_labels / (img_path.stem + ".txt")
            if not label_path.exists():
                continue
            shutil.copy2(img_path, img_out / img_path.name)
            shutil.copy2(label_path, lbl_out / label_path.name)

        counts[split_name] = len(images)
        print(f"  {split_name:6s}: {counts[split_name]:,} images → {img_out}")

    return counts


# ── Step 7: Rewrite dataset.yaml ──────────────────────────────────────────────

def write_dataset_yaml(confirmed_classes: list[str]) -> None:
    """Rewrite data/dataset.yaml with confirmed class list and counts."""
    import yaml

    yaml_data = {
        "path": str(DATA_DIR.relative_to(ROOT)),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc": len(confirmed_classes),
        "names": confirmed_classes,
    }

    yaml_path = DATA_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\n[YAML] Updated {yaml_path} with {len(confirmed_classes)} classes")


# ── Step 8: Coverage report ───────────────────────────────────────────────────

def print_coverage_report(pool_dir: Path, split_counts: dict[str, int]) -> None:
    """Count images per class in the pool and print a coverage table."""
    label_dir = pool_dir / "labels"
    class_counts: dict[str, int] = {c: 0 for c in TARGET_CLASSES}

    for lf in label_dir.glob("*.txt"):
        for line in lf.read_text().strip().splitlines():
            parts = line.split()
            if parts:
                idx = int(parts[0])
                if idx < len(TARGET_CLASSES):
                    class_counts[TARGET_CLASSES[idx]] += 1

    print("\n" + "="*55)
    print("  Dataset Coverage Report")
    print("="*55)
    print(f"  {'Class':<20} {'Bboxes':>8}  {'Status'}")
    print("-"*55)
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        status = "✅ Good" if count >= 500 else ("⚠ Low" if count >= 100 else "❌ Scarce")
        print(f"  {cls:<20} {count:>8,}  {status}")
    print("="*55)
    print(f"\n  Split summary:")
    for split, count in split_counts.items():
        print(f"    {split:6s}: {count:,} images")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    print("\n" + "="*60)
    print("  Food Ingredient Dataset Preparation Pipeline")
    print("="*60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    POOL_DIR.mkdir(parents=True, exist_ok=True)

    source_dirs: list[Path] = []

    # ── Step 1: Roboflow downloads ────────────────────────────────────
    if not args.skip_roboflow:
        print("\n[Step 1/7] Downloading Roboflow datasets …")
        try:
            rf_dirs = download_roboflow(RAW_DIR)
            source_dirs.extend(rf_dirs)
        except SystemExit as e:
            print(f"\n  Roboflow skipped: {e}")
    else:
        print("\n[Step 1/7] Skipping Roboflow downloads (--skip-roboflow)")
        source_dirs.extend([RAW_DIR / ds["name"] for ds in ROBOFLOW_DATASETS if (RAW_DIR / ds["name"]).exists()])

    # ── Step 2: Mendeley dataset ──────────────────────────────────────
    if not args.skip_mendeley:
        print("\n[Step 2/7] Checking Mendeley dataset …")
        mendeley_dir = prepare_mendeley(RAW_DIR)
    else:
        print("\n[Step 2/7] Skipping Mendeley (--skip-mendeley)")
        mendeley_dir = RAW_DIR / "mendeley_vegetables" if (RAW_DIR / "mendeley_vegetables").exists() else None

    # ── Step 3: Convert Mendeley VOC XML → YOLO ───────────────────────
    if mendeley_dir and mendeley_dir.exists():
        print("\n[Step 3/7] Converting Mendeley VOC XML → YOLO TXT …")
        xml_src = mendeley_dir
        yolo_out = mendeley_dir / "labels_yolo"
        n_converted = convert_voc_to_yolo(xml_src, yolo_out, TARGET_CLASSES)
        print(f"  Converted {n_converted} annotation files")
        source_dirs.append(mendeley_dir)
    else:
        print("\n[Step 3/7] Mendeley not available — skipping VOC conversion")

    if not source_dirs:
        print(
            "\nNo datasets found. Either:\n"
            "  1. Add your ROBOFLOW_API_KEY to .env and re-run\n"
            "  2. Manually place datasets in data/raw/ and re-run with --skip-roboflow"
        )
        return

    # ── Step 4 + 5: Normalize & merge into pool ───────────────────────
    print("\n[Step 4/7] Normalizing class names …")
    print("[Step 5/7] Merging all sources into pool …")
    merge_into_pool(source_dirs, POOL_DIR)

    pool_images = list((POOL_DIR / "images").glob("*"))
    if not pool_images:
        print("\nPool is empty after merge. Check your source directories and class mappings.")
        return

    print(f"\n  Pool total: {len(pool_images):,} images")

    # ── Step 6: Split ─────────────────────────────────────────────────
    print(f"\n[Step 6/7] Splitting (train={1-args.val_ratio-args.test_ratio:.0%} / "
          f"val={args.val_ratio:.0%} / test={args.test_ratio:.0%}) …")
    split_counts = split_dataset(
        POOL_DIR, FINAL_DIR,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    # ── Step 7: Rewrite dataset.yaml ──────────────────────────────────
    print("\n[Step 7/7] Writing dataset.yaml …")
    write_dataset_yaml(TARGET_CLASSES)

    # ── Coverage report ───────────────────────────────────────────────
    print_coverage_report(POOL_DIR, split_counts)

    print("Pipeline complete. Next step:")
    print("  python training/train.py --model yolo11m.pt --epochs 50\n")


if __name__ == "__main__":
    main()

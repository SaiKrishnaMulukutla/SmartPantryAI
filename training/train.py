"""
Training script for the food ingredient detector.

Usage:
    python training/train.py [options]

Examples:
    # Fine-tune with defaults (yolo11m, 50 epochs, imgsz=640)
    python training/train.py

    # Custom run
    python training/train.py --model yolo11s.pt --epochs 80 --imgsz 640 --batch 16

    # Resume interrupted training
    python training/train.py --resume

Trained weights are saved to:
    models/food_yolo11/best.pt
    models/food_yolo11/last.pt
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "dataset.yaml"
OUTPUT_DIR = ROOT / "models" / "food_yolo11"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a YOLOv11 food ingredient detector")
    p.add_argument("--model", default="yolo11m.pt",
                   help="Pretrained checkpoint to fine-tune from (default: yolo11m.pt)")
    p.add_argument("--epochs", type=int, default=50,
                   help="Number of training epochs (default: 50)")
    p.add_argument("--imgsz", type=int, default=640,
                   help="Input image size in pixels (default: 640)")
    p.add_argument("--batch", type=int, default=16,
                   help="Batch size — use -1 for auto-batch (default: 16)")
    p.add_argument("--workers", type=int, default=8,
                   help="DataLoader worker threads (default: 8)")
    p.add_argument("--device", default=None,
                   help="Training device: 'cpu', '0', '0,1', etc. (default: auto)")
    p.add_argument("--patience", type=int, default=15,
                   help="Early stopping patience in epochs (default: 15)")
    p.add_argument("--resume", action="store_true",
                   help="Resume from last.pt if a previous run was interrupted")
    p.add_argument("--name", default="food_yolo11",
                   help="Run name inside the project output folder")
    return p.parse_args()


def train(args: argparse.Namespace) -> Path:
    print(f"\n{'='*60}")
    print("  Food Ingredient YOLO Trainer")
    print(f"{'='*60}")
    print(f"  Model      : {args.model}")
    print(f"  Data       : {DATA_YAML}")
    print(f"  Epochs     : {args.epochs}")
    print(f"  Image size : {args.imgsz}px")
    print(f"  Batch size : {args.batch}")
    print(f"  Output     : {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"Dataset config not found at {DATA_YAML}.\n"
            "Ensure your labelled images are placed under data/images/ and labels under data/labels/."
        )

    # If resuming, use last.pt from the previous run
    model_path = str(OUTPUT_DIR / "last.pt") if args.resume and (OUTPUT_DIR / "last.pt").exists() else args.model
    model = YOLO(model_path)

    results = model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        patience=args.patience,
        project=str(ROOT / "runs" / "train"),
        name=args.name,
        exist_ok=True,
        pretrained=True,
        verbose=True,
    )

    # Copy best weights to canonical output location
    run_dir = Path(results.save_dir)
    best_src = run_dir / "weights" / "best.pt"
    last_src = run_dir / "weights" / "last.pt"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if best_src.exists():
        shutil.copy2(best_src, OUTPUT_DIR / "best.pt")
        print(f"\nBest weights saved to: {OUTPUT_DIR / 'best.pt'}")
    if last_src.exists():
        shutil.copy2(last_src, OUTPUT_DIR / "last.pt")

    print(f"Training run artifacts at : {run_dir}")
    print("\nDone. Run `python training/evaluate.py` to evaluate on the test set.")
    return OUTPUT_DIR / "best.pt"


if __name__ == "__main__":
    args = parse_args()
    train(args)

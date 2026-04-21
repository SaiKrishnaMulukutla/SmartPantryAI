"""
Evaluate the trained food ingredient detector on the test split.

Usage:
    python training/evaluate.py [options]

Examples:
    # Evaluate best.pt on the test set
    python training/evaluate.py

    # Evaluate a specific checkpoint
    python training/evaluate.py --weights runs/train/food_yolo11/weights/best.pt

    # Evaluate on validation split instead
    python training/evaluate.py --split val

Prints mAP@0.5, mAP@0.5:0.95, precision, recall per class.
Target: mAP@0.5 > 0.75 before integrating with the app.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "dataset.yaml"
DEFAULT_WEIGHTS = ROOT / "models" / "food_yolo11" / "best.pt"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a trained YOLO food detector")
    p.add_argument("--weights", default=str(DEFAULT_WEIGHTS),
                   help=f"Path to model weights (default: {DEFAULT_WEIGHTS})")
    p.add_argument("--split", choices=["val", "test"], default="test",
                   help="Dataset split to evaluate on (default: test)")
    p.add_argument("--imgsz", type=int, default=640,
                   help="Inference image size (default: 640)")
    p.add_argument("--conf", type=float, default=0.25,
                   help="Confidence threshold for evaluation (default: 0.25)")
    p.add_argument("--iou", type=float, default=0.6,
                   help="IoU threshold for NMS (default: 0.6)")
    p.add_argument("--device", default=None,
                   help="Device: 'cpu', '0', etc. (default: auto)")
    p.add_argument("--save-json", action="store_true",
                   help="Save results to a COCO-format JSON file")
    return p.parse_args()


def evaluate(args: argparse.Namespace) -> None:
    weights = Path(args.weights)
    if not weights.exists():
        raise FileNotFoundError(
            f"Weights not found at {weights}.\n"
            "Run `python training/train.py` first to produce a trained model."
        )
    if not DATA_YAML.exists():
        raise FileNotFoundError(f"Dataset config not found at {DATA_YAML}.")

    print(f"\n{'='*60}")
    print("  Food Ingredient YOLO Evaluator")
    print(f"{'='*60}")
    print(f"  Weights    : {weights}")
    print(f"  Data       : {DATA_YAML}")
    print(f"  Split      : {args.split}")
    print(f"  Conf thr.  : {args.conf}")
    print(f"  IoU thr.   : {args.iou}")
    print(f"{'='*60}\n")

    model = YOLO(str(weights))

    metrics = model.val(
        data=str(DATA_YAML),
        split=args.split,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        save_json=args.save_json,
        verbose=True,
    )

    # ── Summary ──────────────────────────────────────────────────────
    map50 = metrics.box.map50
    map50_95 = metrics.box.map

    print(f"\n{'='*60}")
    print("  Evaluation Results")
    print(f"{'='*60}")
    print(f"  mAP@0.5        : {map50:.4f}  {'✅ PASS (>0.75)' if map50 >= 0.75 else '❌ FAIL (<0.75 — needs more training)'}")
    print(f"  mAP@0.5:0.95   : {map50_95:.4f}")
    print(f"  Precision      : {metrics.box.mp:.4f}")
    print(f"  Recall         : {metrics.box.mr:.4f}")
    print(f"{'='*60}\n")

    if map50 < 0.75:
        print("Suggestions to improve:")
        print("  1. Increase epochs: python training/train.py --epochs 80")
        print("  2. Use a larger model: --model yolo11l.pt")
        print("  3. Add more labelled images (aim for 300+ per class)")
        print("  4. Check annotations for labelling errors\n")
    else:
        print("Model is ready for integration. Run `python training/export.py` to export.\n")


if __name__ == "__main__":
    args = parse_args()
    evaluate(args)

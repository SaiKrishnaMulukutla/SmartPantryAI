"""
Export the trained model to deployment formats.

Usage:
    python training/export.py [options]

Examples:
    # Export to ONNX (recommended for CPU / cross-platform)
    python training/export.py --format onnx

    # Export to TorchScript (default)
    python training/export.py

    # Export to multiple formats at once
    python training/export.py --format onnx tflite

    # Export for Raspberry Pi (NCNN)
    python training/export.py --format ncnn

Supported formats:
    torchscript  — PyTorch TorchScript (fast CPU)
    onnx         — ONNX (cross-platform, OpenCV DNN compatible)
    tflite       — TensorFlow Lite (mobile / embedded)
    ncnn         — NCNN (Raspberry Pi / ARM)
    coreml       — CoreML (Apple devices)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = ROOT / "models" / "food_yolo11" / "best.pt"

SUPPORTED_FORMATS = ["torchscript", "onnx", "tflite", "ncnn", "coreml", "openvino"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export trained YOLO food detector to deployment formats")
    p.add_argument("--weights", default=str(DEFAULT_WEIGHTS),
                   help=f"Path to model weights (default: {DEFAULT_WEIGHTS})")
    p.add_argument("--format", nargs="+", default=["onnx"],
                   choices=SUPPORTED_FORMATS,
                   help="Export format(s) (default: onnx)")
    p.add_argument("--imgsz", type=int, default=640,
                   help="Export image size (default: 640)")
    p.add_argument("--half", action="store_true",
                   help="Export with FP16 half-precision (GPU only)")
    p.add_argument("--dynamic", action="store_true",
                   help="Enable dynamic input shapes (ONNX only)")
    p.add_argument("--simplify", action="store_true", default=True,
                   help="Simplify ONNX graph (default: True)")
    p.add_argument("--device", default=None,
                   help="Device for export: 'cpu', '0', etc. (default: auto)")
    return p.parse_args()


def export(args: argparse.Namespace) -> None:
    weights = Path(args.weights)
    if not weights.exists():
        raise FileNotFoundError(
            f"Weights not found at {weights}.\n"
            "Run `python training/train.py` first."
        )

    print(f"\n{'='*60}")
    print("  Food Ingredient YOLO Exporter")
    print(f"{'='*60}")
    print(f"  Weights  : {weights}")
    print(f"  Formats  : {', '.join(args.format)}")
    print(f"  Img size : {args.imgsz}px")
    print(f"  FP16     : {args.half}")
    print(f"{'='*60}\n")

    model = YOLO(str(weights))
    exported_paths: list[str] = []

    for fmt in args.format:
        print(f"Exporting to {fmt.upper()}…")
        try:
            out = model.export(
                format=fmt,
                imgsz=args.imgsz,
                half=args.half,
                dynamic=args.dynamic if fmt == "onnx" else False,
                simplify=args.simplify if fmt == "onnx" else False,
                device=args.device,
            )
            exported_paths.append(str(out))
            print(f"  Saved to: {out}\n")
        except Exception as exc:
            print(f"  Export to {fmt} failed: {exc}\n")

    # ── Summary ──────────────────────────────────────────────────────
    if exported_paths:
        print(f"{'='*60}")
        print("  Exported Files")
        print(f"{'='*60}")
        for path in exported_paths:
            print(f"  {path}")
        print(f"{'='*60}\n")

        if any("onnx" in p for p in exported_paths):
            print("To run inference with the ONNX model:")
            print("  from ultralytics import YOLO")
            print("  model = YOLO('models/food_yolo11/best.onnx')")
            print("  results = model('your_image.jpg')\n")


if __name__ == "__main__":
    args = parse_args()
    export(args)

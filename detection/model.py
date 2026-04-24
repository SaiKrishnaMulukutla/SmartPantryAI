from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw
from ultralytics import YOLO


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


@dataclass
class InferenceResult:
    labels: list[str]            # deduplicated ingredient names
    annotated_image: np.ndarray  # RGB frame with bounding boxes drawn
    raw_boxes: list[dict] = field(default_factory=list)


class YOLODetector:
    """YOLOv11 inference wrapper for food ingredient detection."""

    _PALETTE = [
        (0, 200, 100),
        (0, 140, 255),
        (255, 80, 80),
        (180, 0, 255),
        (255, 200, 0),
        (0, 220, 220),
        (255, 120, 0),
        (80, 180, 255),
    ]

    def __init__(self, model_path: str, confidence: float = 0.5) -> None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model weights not found at '{model_path}'.\n"
                "Train a custom model first (see training/train.py) or download "
                "a pretrained checkpoint and place it at the path above."
            )
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.class_names: list[str] = list(self.model.names.values())

    @classmethod
    def from_pretrained(cls, model_name: str = "yolo11m.pt", confidence: float = 0.5) -> "YOLODetector":
        instance = object.__new__(cls)
        instance.model = YOLO(model_name)
        instance.confidence = confidence
        instance.class_names = list(instance.model.names.values())
        return instance

    def detect(self, frame_rgb: np.ndarray) -> list[Detection]:
        """Run inference on an RGB frame, return detections above confidence threshold."""
        results = self.model(frame_rgb, conf=self.confidence, iou=0.45, max_det=50, verbose=False)
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = self.class_names[cls_id] if cls_id < len(self.class_names) else str(cls_id)
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(Detection(label=label, confidence=conf, bbox=(x1, y1, x2, y2)))
        return detections

    def draw_boxes(self, frame_rgb: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """Draw bounding boxes onto a copy of the RGB frame using PIL."""
        img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(img)
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cls_idx = self.class_names.index(det.label) if det.label in self.class_names else 0
            colour = self._PALETTE[cls_idx % len(self._PALETTE)]
            draw.rectangle([x1, y1, x2, y2], outline=colour, width=2)
            label_text = f"{det.label} {det.confidence:.0%}"
            text_w = len(label_text) * 7
            draw.rectangle([x1, y1 - 20, x1 + text_w, y1], fill=colour)
            draw.text((x1 + 3, y1 - 18), label_text, fill=(255, 255, 255))
        return np.array(img)

    def unique_labels(self, detections: list[Detection]) -> list[str]:
        return list(dict.fromkeys(d.label for d in detections))


def run_inference(detector: YOLODetector, frame_rgb: np.ndarray) -> InferenceResult:
    """Run detection and return a fully-typed InferenceResult."""
    detections = detector.detect(frame_rgb)
    annotated_rgb = detector.draw_boxes(frame_rgb, detections)
    return InferenceResult(
        labels=detector.unique_labels(detections),
        annotated_image=annotated_rgb,
        raw_boxes=[
            {"label": d.label, "confidence": d.confidence, "bbox": d.bbox}
            for d in detections
        ],
    )

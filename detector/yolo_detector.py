from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


class YOLODetector:
    """YOLOv11 inference wrapper for food ingredient detection."""

    # Colour palette — one colour per class index (cycles if >len)
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
        """Load a pretrained Ultralytics checkpoint by name (downloads automatically)."""
        instance = object.__new__(cls)
        instance.model = YOLO(model_name)
        instance.confidence = confidence
        instance.class_names = list(instance.model.names.values())
        return instance

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a single BGR frame, return detections above confidence threshold."""
        results = self.model(frame, conf=self.confidence, verbose=False)
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

    def draw_boxes(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """Draw bounding boxes and labels onto a copy of the frame."""
        output = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cls_idx = self.class_names.index(det.label) if det.label in self.class_names else 0
            colour = self._PALETTE[cls_idx % len(self._PALETTE)]

            # Box
            cv2.rectangle(output, (x1, y1), (x2, y2), colour, 2)

            # Label background
            label_text = f"{det.label} {det.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(output, (x1, y1 - th - 8), (x1 + tw + 6, y1), colour, -1)

            # Label text
            cv2.putText(
                output, label_text,
                (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

        return output

    def unique_labels(self, detections: list[Detection]) -> list[str]:
        """Return deduplicated ingredient names from a detection list."""
        return list(dict.fromkeys(d.label for d in detections))

from __future__ import annotations

import cv2
import numpy as np


class FrameProcessor:
    """OpenCV webcam capture and frame preprocessing."""

    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Context manager support — use as `with FrameProcessor() as fp:`
    # ------------------------------------------------------------------

    def open(self) -> "FrameProcessor":
        self._cap = cv2.VideoCapture(self.camera_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera at index {self.camera_index}. "
                "Check that a webcam is connected and not in use by another application."
            )
        return self

    def close(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None

    def __enter__(self) -> "FrameProcessor":
        return self.open()

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def read_frame(self) -> np.ndarray | None:
        """Read one frame from the camera. Returns None on failure."""
        if self._cap is None or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        return frame if ret else None

    def read_frame_rgb(self) -> np.ndarray | None:
        """Read one frame and convert from BGR to RGB (for Streamlit/PIL)."""
        frame = self.read_frame()
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # ------------------------------------------------------------------
    # Preprocessing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def resize(frame: np.ndarray, width: int, height: int) -> np.ndarray:
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    @staticmethod
    def rgb_to_bgr(frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    @staticmethod
    def encode_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
        """Encode a BGR frame as JPEG bytes (for Streamlit st.image)."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def get_resolution(self) -> tuple[int, int]:
        """Return actual (width, height) reported by the capture device."""
        if not self.is_open:
            return (self.width, self.height)
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w, h)

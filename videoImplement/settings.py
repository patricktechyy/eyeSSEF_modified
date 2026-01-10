"""User-facing configuration for preprocessing.

This module centralises the recording parameters (fps, resolution) so every preprocessing
pass can compute time-based thresholds correctly.

Notes on calibration:
- Your project uses a pixel->mm conversion (px_to_mm, pixels per millimeter).
- The default here scales from your historical anchor: at 1920x1080 you used px_to_mm ≈ 30.
- This resolution-based scaling is an approximation; for best accuracy, calibrate px_to_mm
  using a known-size object at the same camera distance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import re

import pandas as pd

# Calibration anchor used in your project:
# At 1920x1080, you previously used pxToMm = 30 (pixels per mm).
_BASE_RES = (1920, 1080)
_BASE_PX_TO_MM = 30.0


def parse_resolution(res_str: str) -> Tuple[int, int]:
    """Parse '1920x1080' -> (1920,1080)."""
    m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", res_str)
    if not m:
        raise ValueError(f"Invalid resolution format: {res_str} (expected like 1920x1080)")
    return int(m.group(1)), int(m.group(2))


def px_to_mm_from_resolution(width: int, height: int) -> float:
    """Estimate px_to_mm from resolution by scaling on vertical dimension.

    This assumes the same optics and camera distance, so the pupil occupies a similar
    fraction of the frame. If those change, you should calibrate px_to_mm directly.
    """
    base_w, base_h = _BASE_RES
    return _BASE_PX_TO_MM * (height / base_h)


def infer_fps_from_timestamps(df: pd.DataFrame) -> int:
    """Infer fps from timestamp differences (requires 'timestamp' column)."""
    if "timestamp" not in df.columns:
        raise ValueError("Cannot infer fps: 'timestamp' column missing.")
    dt = pd.to_numeric(df["timestamp"], errors="coerce").diff().dropna()
    if dt.empty:
        raise ValueError("Cannot infer fps: not enough timestamp samples.")
    median_dt = float(dt.median())
    if median_dt <= 0:
        raise ValueError("Cannot infer fps: invalid timestamp deltas.")
    return int(round(1.0 / median_dt))


@dataclass
class ProcessingConfig:
    """Configuration shared by all preprocessing passes."""
    fps: float
    resolution: Tuple[int, int]
    px_to_mm: Optional[float] = None  # pixels per mm
    confidence_thresh: float = 0.75

    # time-based parameters
    max_gap_ms: int = 400           # Pass 4 interpolation
    savgol_window_ms: int = 150     # Pass 6 smoothing window

    def __post_init__(self):
        if self.px_to_mm is None:
            self.px_to_mm = px_to_mm_from_resolution(self.width, self.height)

    @property
    def width(self) -> int:
        return int(self.resolution[0])

    @property
    def height(self) -> int:
        return int(self.resolution[1])

    @property
    def res_str(self) -> str:
        return f"{self.width}x{self.height}"

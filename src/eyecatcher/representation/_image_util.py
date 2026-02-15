"""Shared image encoding for grid representations."""

from __future__ import annotations

import base64
import io

import numpy as np


def rgb_to_png_base64(arr: np.ndarray) -> str:
    """Encode (H, W, 3) uint8 RGB array as PNG base64 (no data URL prefix)."""
    from PIL import Image

    arr = np.asarray(arr)
    if arr.ndim != 3 or arr.shape[2] != 3:
        arr = np.stack([arr, arr, arr], axis=-1) if arr.ndim == 2 else arr
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

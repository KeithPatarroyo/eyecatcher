"""Shared image encoding for grid representations."""

from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np

from .protocol import RepresentationOutput


def serialize_grid_image(output: RepresentationOutput) -> dict[str, Any]:
    """Convert grid RepresentationOutput to API-ready image + grid dict.

    Returns {"image": "data:image/png;base64,...", "grid": nested_list}.
    Used by GridRepresentationBase.serialize_output.
    """
    if output.output_type != "grid" or not hasattr(output.data, "shape"):
        return {"image": "", "grid": []}
    arr = np.asarray(output.data)
    b64 = rgb_to_png_base64(arr)
    if arr.ndim >= 2:
        grid_01 = (
            (arr[:, :, 0] > 0).astype(np.uint8)
            if arr.ndim == 3
            else np.clip(arr, 0, 1).astype(np.uint8)
        )
        grid_list = grid_01.tolist()
    else:
        grid_list = []
    return {"image": "data:image/png;base64," + b64, "grid": grid_list}


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

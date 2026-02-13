"""
Shared helpers for API route responses.

Provides consistent error response format and shared error message constants
so wording and API contract can be tuned in one place.
Save helpers: numpy_to_png_base64, build_save_zip_response for /api/save handlers.
Error handling: api_try_except decorator for route handlers.
"""

import base64
import io
import zipfile
from functools import wraps

import numpy as np
from flask import Response, jsonify

# Shared API error messages (validation / required fields)
# Individual = genome + metadata (key, fitness); the unit of evolution in the API.
ERR_INDIVIDUAL_REQUIRED = "individual required"
ERR_INDIVIDUAL_REQUIRED_BODY = "individual required in request body"
ERR_INDIVIDUALS_ARRAY_REQUIRED = "individuals array required"
ERR_PARENTS_ARRAY_REQUIRED = "parents array required"
ERR_ID_REQUIRED = "id required"
# Legacy names for code that still references them (e.g. error message substrings)
ERR_GENOME_REQUIRED = ERR_INDIVIDUAL_REQUIRED
ERR_GENOME_REQUIRED_BODY = ERR_INDIVIDUAL_REQUIRED_BODY
ERR_GENOME_OBJECT_REQUIRED = "individual object required"
ERR_GENOMES_ARRAY_REQUIRED = ERR_INDIVIDUALS_ARRAY_REQUIRED


def api_error(message: str, status: int = 400):
    """
    Return a JSON error response with consistent shape.

    Args:
        message: Error message string (e.g. str(e)).
        status: HTTP status code (default 400).

    Returns:
        Tuple of (Response, status_code) for use in route return.
    """
    return jsonify({"error": message}), status


def api_try_except(fn):
    """Decorator: ValueError -> 400, Exception -> 500. Use on route handlers."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as e:
            return api_error(str(e), 400)
        except Exception as e:
            return api_error(str(e), 500)

    return wrapper


def numpy_to_png_base64(arr: np.ndarray) -> str:
    """
    Encode a numpy image array as PNG base64 string.

    Handles 2D (grayscale) by stacking to RGB; normalizes to uint8 0-255.
    """
    from PIL import Image

    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_save_zip_response(
    individual_id: int,
    assets: dict[str, bytes],
    zip_filename: str,
) -> Response:
    """
    Build a zip from filename->bytes, return JSON response for client download.

    assets: filename (e.g. pattern_1.png) -> raw bytes.
    zip_filename: name for the zip in the downloads list (e.g. pattern_1.zip).
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in assets.items():
            zf.writestr(name, data)
    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("ascii")
    return jsonify(
        {
            "id": individual_id,
            "status": "saved",
            "downloads": [
                {
                    "filename": zip_filename,
                    "mime": "application/zip",
                    "content_base64": zip_base64,
                },
            ],
        }
    )

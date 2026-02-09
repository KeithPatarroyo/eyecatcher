"""
Shared helpers for API route responses.

Provides consistent error response format so changes (e.g. request ID)
can be made in one place.
"""

from flask import jsonify


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

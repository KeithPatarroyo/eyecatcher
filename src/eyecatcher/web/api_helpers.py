"""
Shared helpers for API route responses.

Provides consistent error response format and shared error message constants
so wording and API contract can be tuned in one place.
"""

from flask import jsonify

# Shared API error messages (validation / required fields)
ERR_GENOME_REQUIRED = "genome required"
ERR_GENOME_REQUIRED_REQUEST_BODY = "genome required in request body"
ERR_GENOME_OBJECT_REQUIRED = "genome object required"
ERR_GENOMES_ARRAY_REQUIRED = "genomes array required"
ERR_PARENTS_ARRAY_REQUIRED = "parents array required"
ERR_ID_REQUIRED = "id required"


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

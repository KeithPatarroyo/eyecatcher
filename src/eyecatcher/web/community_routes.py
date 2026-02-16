"""
Community API Blueprint for Eyecatcher.

Provides endpoints for community pattern submissions and admin moderation:
- /api/community/submit: Submit a pattern for review
- /api/community: Get approved patterns
- /api/admin/*: Moderation endpoints (requires ADMIN_KEY)
"""

import json
import logging
import os
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request

from ..data import default_db_path, with_db_connection
from .api_helpers import (
    ERR_ID_REQUIRED,
    ERR_INDIVIDUAL_OBJECT_REQUIRED,
    api_error,
    api_try_except,
)

logger = logging.getLogger(__name__)

# Create blueprint
community_bp = Blueprint("community", __name__)


# Database path (configurable via environment)
DATABASE_PATH = os.environ.get("DATABASE_PATH") or default_db_path("community.db")


def _init_community_db():
    """Initialize the community submissions table."""
    with with_db_connection(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                creator TEXT,
                genome_json TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP,
                approved_at TIMESTAMP
            )
        """)
        conn.commit()


# Initialize DB on module load
_init_community_db()


def _rows_to_dicts(rows, extra_keys):
    """Parse rows: genome=parsed genome_json + extra_keys. Skips invalid JSON."""
    result = []
    for row in rows:
        row_dict = dict(row)
        try:
            genome = json.loads(row_dict["genome_json"])
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
        item = {"individual": genome}
        for k in extra_keys:
            if k in row_dict:
                item[k] = row_dict[k]
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Admin key configuration
# ---------------------------------------------------------------------------

# Default to ALICE when unset so local dev works without setting env
ADMIN_KEY = (os.environ.get("ADMIN_KEY") or "ALICE").strip()
# Normalize: strip carriage returns (env can have \r in some Docker setups)
ADMIN_KEY = ADMIN_KEY.replace("\r", "").replace("\n", "").strip()


def _normalize_key(raw):
    """Normalize key from request for comparison."""
    if raw is None:
        return ""
    s = str(raw).strip().replace("\r", "").replace("\n", "")
    return s


def _check_admin_key():
    """Check if request has valid admin key (header X-Admin-Key or query admin_key)."""
    raw = request.headers.get("X-Admin-Key") or request.args.get("admin_key")
    key = _normalize_key(raw)
    # In development, always accept ALICE so it works regardless of env
    if os.environ.get("FLASK_ENV") == "development" and key == "ALICE":
        return True, None, None
    if not ADMIN_KEY:
        return False, *api_error("Admin key not configured", 500)
    if key != ADMIN_KEY:
        if os.environ.get("FLASK_ENV") == "development":
            logger.warning(
                "Admin key mismatch: expected len=%s got len=%s key_repr=%r",
                len(ADMIN_KEY),
                len(key),
                key,
            )
        return False, *api_error("Invalid admin key", 403)
    return True, None, None


def require_admin(f):
    """Decorator: return error response if admin key check fails."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        ok, err_response, status = _check_admin_key()
        if not ok:
            return err_response, status
        return f(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Community submission endpoints
# ---------------------------------------------------------------------------


@community_bp.route("/api/community/submit", methods=["POST"])
@api_try_except
def api_community_submit():
    """POST /api/community/submit: body individual, name, creator; returns id, status."""  # noqa: E501
    data = request.json or {}
    individual = data.get("individual")
    name = (data.get("name") or "").strip() or "Unnamed"
    creator = (data.get("creator") or "").strip() or "Anonymous"
    if not individual or not isinstance(individual, dict):
        return api_error(ERR_INDIVIDUAL_OBJECT_REQUIRED, 400)
    genome_json = json.dumps(individual)
    with with_db_connection(DATABASE_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO submissions
               (name, creator, genome_json, status, submitted_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (name, creator, genome_json, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        sid = cur.lastrowid
    return jsonify({"id": sid, "status": "pending"})


@community_bp.route("/api/community", methods=["GET"])
@api_try_except
def api_community():
    """GET /api/community: approved patterns (id, name, creator, genome)."""
    with with_db_connection(DATABASE_PATH) as conn:
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, approved_at
               FROM submissions WHERE status = 'approved'
               ORDER BY approved_at DESC"""
        ).fetchall()
    patterns = _rows_to_dicts(rows, ["id", "name", "creator", "approved_at"])
    return jsonify({"patterns": patterns})


# ---------------------------------------------------------------------------
# Admin moderation endpoints
# ---------------------------------------------------------------------------


@community_bp.route("/api/admin/status", methods=["GET"])
def api_admin_status():
    """GET /api/admin/status: admin key configured and length (debug 403). No auth."""
    return jsonify(
        {
            "configured": bool(ADMIN_KEY),
            "key_length": len(ADMIN_KEY),
        }
    )


@community_bp.route("/api/admin/submissions", methods=["GET"])
@api_try_except
@require_admin
def api_admin_submissions():
    """GET /api/admin/submissions: list pending. Admin only; X-Admin-Key."""
    with with_db_connection(DATABASE_PATH) as conn:
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, status, submitted_at
               FROM submissions WHERE status = 'pending'
               ORDER BY submitted_at ASC"""
        ).fetchall()
    submissions = _rows_to_dicts(
        rows, ["id", "name", "creator", "status", "submitted_at"]
    )
    return jsonify({"submissions": submissions})


def _admin_moderate(action):
    """Approve or reject a submission. Used by api_admin_approve / api_admin_reject."""
    data = request.json or {}
    submission_id = data.get("id")
    if not submission_id:
        return api_error(ERR_ID_REQUIRED, 400)
    if action == "approve":
        sql = (
            "UPDATE submissions SET status = 'approved', approved_at = ? "
            "WHERE id = ? AND status = 'pending'"
        )
        params = (datetime.now(timezone.utc).isoformat(), submission_id)
        status_val = "approved"
    else:
        sql = (
            "UPDATE submissions SET status = 'rejected' "
            "WHERE id = ? AND status = 'pending'"
        )
        params = (submission_id,)
        status_val = "rejected"
    with with_db_connection(DATABASE_PATH) as conn:
        conn.execute(sql, params)
        conn.commit()
    return jsonify({"id": submission_id, "status": status_val})


@community_bp.route("/api/admin/approve", methods=["POST"])
@api_try_except
@require_admin
def api_admin_approve():
    """POST /api/admin/approve: body id; approve. Admin only; X-Admin-Key."""
    return _admin_moderate("approve")


@community_bp.route("/api/admin/reject", methods=["POST"])
@api_try_except
@require_admin
def api_admin_reject():
    """POST /api/admin/reject: body id; reject. Admin only; X-Admin-Key."""
    return _admin_moderate("reject")

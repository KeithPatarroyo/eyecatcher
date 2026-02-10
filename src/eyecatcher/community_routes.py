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

from flask import Blueprint, jsonify, request

from .api_helpers import ERR_GENOME_OBJECT_REQUIRED, ERR_ID_REQUIRED, api_error
from .db_util import default_db_path, with_db_connection

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


# ---------------------------------------------------------------------------
# Community submission endpoints
# ---------------------------------------------------------------------------


@community_bp.route("/api/community/submit", methods=["POST"])
def api_community_submit():
    """POST /api/community/submit: body genome, name, creator; returns id, status."""
    try:
        data = request.json or {}
        genome = data.get("genome")
        name = (data.get("name") or "").strip() or "Unnamed"
        creator = (data.get("creator") or "").strip() or "Anonymous"
        if not genome or not isinstance(genome, dict):
            return api_error(ERR_GENOME_OBJECT_REQUIRED, 400)
        genome_json = json.dumps(genome)
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
    except Exception as e:
        return api_error(str(e), 500)


@community_bp.route("/api/community", methods=["GET"])
def api_community():
    """GET /api/community: approved patterns (id, name, creator, genome)."""
    try:
        with with_db_connection(DATABASE_PATH) as conn:
            rows = conn.execute(
                """SELECT id, name, creator, genome_json, approved_at
                   FROM submissions WHERE status = 'approved'
                   ORDER BY approved_at DESC"""
            ).fetchall()
        patterns = []
        for row in rows:
            try:
                genome = json.loads(row["genome_json"])
                patterns.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "creator": row["creator"],
                        "genome": genome,
                        "approved_at": row["approved_at"],
                    }
                )
            except (json.JSONDecodeError, TypeError):
                continue
        return jsonify({"patterns": patterns})
    except Exception as e:
        return api_error(str(e), 500)


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
def api_admin_submissions():
    """GET /api/admin/submissions: list pending. Admin only; X-Admin-Key."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        with with_db_connection(DATABASE_PATH) as conn:
            rows = conn.execute(
                """SELECT id, name, creator, genome_json, status, submitted_at
                   FROM submissions WHERE status = 'pending'
                   ORDER BY submitted_at ASC"""
            ).fetchall()
        submissions = []
        for row in rows:
            try:
                genome = json.loads(row["genome_json"])
                submissions.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "creator": row["creator"],
                        "genome": genome,
                        "status": row["status"],
                        "submitted_at": row["submitted_at"],
                    }
                )
            except (json.JSONDecodeError, TypeError):
                continue
        return jsonify({"submissions": submissions})
    except Exception as e:
        return api_error(str(e), 500)


@community_bp.route("/api/admin/approve", methods=["POST"])
def api_admin_approve():
    """POST /api/admin/approve: body id; approve. Admin only; X-Admin-Key."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get("id")
        if not submission_id:
            return api_error(ERR_ID_REQUIRED, 400)
        with with_db_connection(DATABASE_PATH) as conn:
            conn.execute(
                """UPDATE submissions SET status = 'approved', approved_at = ?
                   WHERE id = ? AND status = 'pending'""",
                (datetime.now(timezone.utc).isoformat(), submission_id),
            )
            conn.commit()
        return jsonify({"id": submission_id, "status": "approved"})
    except Exception as e:
        return api_error(str(e), 500)


@community_bp.route("/api/admin/reject", methods=["POST"])
def api_admin_reject():
    """POST /api/admin/reject: body id; reject. Admin only; X-Admin-Key."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get("id")
        if not submission_id:
            return api_error(ERR_ID_REQUIRED, 400)
        with with_db_connection(DATABASE_PATH) as conn:
            conn.execute(
                """UPDATE submissions SET status = 'rejected'
                   WHERE id = ? AND status = 'pending'""",
                (submission_id,),
            )
            conn.commit()
        return jsonify({"id": submission_id, "status": "rejected"})
    except Exception as e:
        return api_error(str(e), 500)

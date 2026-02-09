"""
Community API Blueprint for Eyecatcher.

Provides endpoints for community pattern submissions and admin moderation:
- /api/community/submit: Submit a pattern for review
- /api/community: Get approved patterns
- /api/admin/*: Moderation endpoints (requires ADMIN_KEY)
"""

import json
import os
import sqlite3
from datetime import datetime

from flask import Blueprint, jsonify, request

# Create blueprint
community_bp = Blueprint("community", __name__)


# Database path (configurable via environment)
def _default_database_path():
    from . import get_root_dir

    return os.path.join(get_root_dir(), "data", "community.db")


DATABASE_PATH = os.environ.get("DATABASE_PATH") or _default_database_path()


def _get_db():
    """Get a connection to the community database."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_community_db():
    """Initialize the community submissions table."""
    conn = _get_db()
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
    conn.close()


# Initialize DB on module load
_init_community_db()


# ---------------------------------------------------------------------------
# Admin key configuration
# ---------------------------------------------------------------------------

# Default to ALICE when unset so local dev works without setting env
ADMIN_KEY = (os.environ.get("ADMIN_KEY") or "ALICE").strip()
# Normalize: strip and remove any carriage returns (env can have \r in some Docker setups)
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
        return False, jsonify({"error": "Admin key not configured"}), 500
    if key != ADMIN_KEY:
        if os.environ.get("FLASK_ENV") == "development":
            import sys

            print(
                "Admin key mismatch: expected len=%d got len=%d key_repr=%r"
                % (len(ADMIN_KEY), len(key), key),
                file=sys.stderr,
            )
        return False, jsonify({"error": "Invalid admin key"}), 403
    return True, None, None


# ---------------------------------------------------------------------------
# Community submission endpoints
# ---------------------------------------------------------------------------


@community_bp.route("/api/community/submit", methods=["POST"])
def api_community_submit():
    """
    Submit a pattern to the community pool.
    Body: { "genome": { key, visual, time_signal }, "name": "...", "creator": "..." }
    Returns: { "id": ..., "status": "pending" }
    """
    try:
        data = request.json or {}
        genome = data.get("genome")
        name = (data.get("name") or "").strip() or "Unnamed"
        creator = (data.get("creator") or "").strip() or "Anonymous"
        if not genome or not isinstance(genome, dict):
            return jsonify({"error": "genome object required"}), 400
        genome_json = json.dumps(genome)
        conn = _get_db()
        cur = conn.execute(
            """INSERT INTO submissions (name, creator, genome_json, status, submitted_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (name, creator, genome_json, datetime.utcnow().isoformat()),
        )
        conn.commit()
        sid = cur.lastrowid
        conn.close()
        return jsonify({"id": sid, "status": "pending"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route("/api/community", methods=["GET"])
def api_community():
    """Return approved community submissions (genome list)."""
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, approved_at
               FROM submissions WHERE status = 'approved' ORDER BY approved_at DESC"""
        ).fetchall()
        conn.close()
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
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Admin moderation endpoints
# ---------------------------------------------------------------------------


@community_bp.route("/api/admin/status", methods=["GET"])
def api_admin_status():
    """Public endpoint: report if admin key is configured and its length (for debugging 403)."""
    return jsonify(
        {
            "configured": bool(ADMIN_KEY),
            "key_length": len(ADMIN_KEY),
        }
    )


@community_bp.route("/api/admin/submissions", methods=["GET"])
def api_admin_submissions():
    """List all pending submissions (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, status, submitted_at
               FROM submissions WHERE status = 'pending' ORDER BY submitted_at ASC"""
        ).fetchall()
        conn.close()
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
        return jsonify({"error": str(e)}), 500


@community_bp.route("/api/admin/approve", methods=["POST"])
def api_admin_approve():
    """Approve a submission (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get("id")
        if not submission_id:
            return jsonify({"error": "id required"}), 400
        conn = _get_db()
        conn.execute(
            """UPDATE submissions SET status = 'approved', approved_at = ?
               WHERE id = ? AND status = 'pending'""",
            (datetime.utcnow().isoformat(), submission_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": submission_id, "status": "approved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route("/api/admin/reject", methods=["POST"])
def api_admin_reject():
    """Reject a submission (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get("id")
        if not submission_id:
            return jsonify({"error": "id required"}), 400
        conn = _get_db()
        conn.execute(
            """UPDATE submissions SET status = 'rejected'
               WHERE id = ? AND status = 'pending'""",
            (submission_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": submission_id, "status": "rejected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

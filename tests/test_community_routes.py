"""Tests for community API (submit, list, admin approve/reject)."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture
def admin_headers():
    """Admin key header for moderation endpoints (ALICE in dev)."""
    return {"X-Admin-Key": "ALICE"}


def test_community_submit(client, community_db, cppn_engine):
    """POST submit with genome returns id and status pending."""
    from eyecatcher.cppn_engine import create_random_dual_genome
    from eyecatcher.genome_serialization import dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0

    rv = client.post(
        "/api/community/submit",
        json={"genome": genome, "name": "Test Pattern", "creator": "Tester"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["id"] == 1
    assert data["status"] == "pending"


def test_community_submit_missing_genome(client, community_db):
    """POST submit without genome returns 400."""
    rv = client.post(
        "/api/community/submit",
        json={"name": "x", "creator": "y"},
    )
    assert rv.status_code == 400
    assert "genome" in rv.get_json().get("error", "").lower()


def test_community_empty(client, community_db):
    """GET community with no submissions returns empty patterns."""
    rv = client.get("/api/community")
    assert rv.status_code == 200
    assert rv.get_json()["patterns"] == []


def test_admin_status(client):
    """GET admin/status returns configured and key_length."""
    rv = client.get("/api/admin/status")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "configured" in data
    assert "key_length" in data


def test_admin_submissions_forbidden_without_key(client, community_db):
    """GET admin/submissions without key returns 403."""
    rv = client.get("/api/admin/submissions")
    assert rv.status_code == 403


def test_admin_submit_then_list_and_approve(
    client, community_db, cppn_engine, admin_headers
):
    """Submit, list pending as admin, approve, then list public shows pattern."""
    from eyecatcher.cppn_engine import create_random_dual_genome
    from eyecatcher.genome_serialization import dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0

    with patch.dict(os.environ, {"FLASK_ENV": "development"}):
        submit_rv = client.post(
            "/api/community/submit",
            json={"genome": genome, "name": "ToApprove", "creator": "Me"},
        )
    assert submit_rv.status_code == 200
    sid = submit_rv.get_json()["id"]

    with patch.dict(os.environ, {"FLASK_ENV": "development"}):
        pending_rv = client.get(
            "/api/admin/submissions",
            headers=admin_headers,
        )
    assert pending_rv.status_code == 200
    subs = pending_rv.get_json()["submissions"]
    assert len(subs) == 1
    assert subs[0]["name"] == "ToApprove"

    with patch.dict(os.environ, {"FLASK_ENV": "development"}):
        approve_rv = client.post(
            "/api/admin/approve",
            json={"id": sid},
            headers=admin_headers,
        )
    assert approve_rv.status_code == 200
    assert approve_rv.get_json()["status"] == "approved"

    list_rv = client.get("/api/community")
    assert list_rv.status_code == 200
    patterns = list_rv.get_json()["patterns"]
    assert len(patterns) == 1
    assert patterns[0]["name"] == "ToApprove"
    assert patterns[0]["creator"] == "Me"

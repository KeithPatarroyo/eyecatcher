"""Tests for genealogy API (save/load population, tree, branches)."""

import pytest
from eyecatcher.genome import create_random_dual_genome, dual_genome_to_json


def _make_individual_payload(representation, key=0):
    """Build dual genome JSON for genealogy API payloads."""
    dual = create_random_dual_genome(
        representation.config, representation.time_config, genome_id=key
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = key
    return payload


def _save_population(
    client,
    individuals,
    parent_id=None,
    generation_num=0,
    branch_name="main",
    description=None,
    **kwargs,
):
    """POST save-population; return response."""
    body = {
        "individuals": individuals,
        "parent_id": parent_id,
        "generation_num": generation_num,
        "branch_name": branch_name,
    }
    if description is not None:
        body["description"] = description
    body.update(kwargs)
    return client.post("/api/genealogy/save-population", json=body)


@pytest.mark.slow
def test_save_population(client, genealogy_db, representation):
    """POST save-population with individuals returns population_id and individual_ids."""  # noqa: E501
    payload = _make_individual_payload(representation, 0)
    rv = _save_population(
        client,
        [payload],
        description="test",
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "population_id" in data
    assert data["population_id"] == 1
    assert data["individual_ids"] == [1]
    assert data["generation_num"] == 0


def test_save_population_empty_individuals(client, genealogy_db):
    """POST save-population without individuals returns 400."""
    rv = client.post(
        "/api/genealogy/save-population",
        json={"individuals": [], "generation_num": 0},
    )
    assert rv.status_code == 400
    assert "individuals" in rv.get_json().get("error", "").lower()


def test_load_population_not_found(client, genealogy_db):
    """GET load-population for missing id returns 404."""
    rv = client.get("/api/genealogy/load-population/99999")
    assert rv.status_code == 404
    assert "not found" in rv.get_json().get("error", "").lower()


@pytest.mark.slow
def test_save_and_load_population(client, genealogy_db, representation):
    """Save a population then load it by id; individuals round-trip."""
    payload = _make_individual_payload(representation, 7)
    save_rv = _save_population(client, [payload])
    assert save_rv.status_code == 200
    pop_id = save_rv.get_json()["population_id"]

    load_rv = client.get(f"/api/genealogy/load-population/{pop_id}")
    assert load_rv.status_code == 200
    data = load_rv.get_json()
    assert data["population_id"] == pop_id
    assert data["generation_num"] == 0
    assert data["branch_name"] == "main"
    assert len(data["individuals"]) == 1
    assert data["individuals"][0]["key"] == 7
    ind0 = data["individuals"][0]
    assert "visual" in ind0 and "time_signal" in ind0


def test_experiment_log_empty(client, genealogy_db):
    """GET experiment-log with no data returns empty entries."""
    rv = client.get("/api/experiment-log")
    assert rv.status_code == 200
    assert rv.get_json()["entries"] == []


@pytest.mark.slow
def test_experiment_log_after_save(client, genealogy_db, representation):
    """GET experiment-log after save-population returns entry with experiment_config."""
    payload = _make_individual_payload(representation, 0)
    _save_population(client, [payload])
    rv = client.get("/api/experiment-log")
    assert rv.status_code == 200
    entries = rv.get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["branch_name"] == "main"
    exp = entries[0].get("metadata", {}).get("experiment_config", {})
    assert "representation_id" in exp or "representation_id" in exp
    assert "population_size" in exp
    assert "crossover_probability" in exp


def test_tree_empty(client, genealogy_db):
    """GET tree with no data returns empty nodes."""
    rv = client.get("/api/genealogy/tree")
    assert rv.status_code == 200
    assert rv.get_json()["nodes"] == []


@pytest.mark.slow
def test_tree_after_save(client, genealogy_db, representation):
    """GET tree after save returns one node."""
    payload = _make_individual_payload(representation, 0)
    _save_population(client, [payload])
    rv = client.get("/api/genealogy/tree")
    assert rv.status_code == 200
    nodes = rv.get_json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["branch_name"] == "main"
    assert nodes[0]["generation_num"] == 0


def test_branches_empty(client, genealogy_db):
    """GET branches with no data returns empty list."""
    rv = client.get("/api/genealogy/branches")
    assert rv.status_code == 200
    assert rv.get_json()["branches"] == []


@pytest.mark.slow
def test_export_genealogy_full(client, genealogy_db, representation):
    """GET export (no branch): full tree; populations, individuals, exported_at."""
    p1 = _make_individual_payload(representation, 0)
    p2 = _make_individual_payload(representation, 1)
    _save_population(client, [p1, p2])
    rv = client.get("/api/genealogy/export")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "exported_at" in data
    assert "version" in data
    assert data["version"] == 1
    assert len(data["populations"]) == 1
    assert len(data["individuals"]) == 2
    for ind in data["individuals"]:
        assert "genome_json" in ind
        assert "population_id" in ind
        assert "genome_key" in ind
        assert "fitness" in ind
        assert "created_at" in ind


@pytest.mark.slow
def test_export_genealogy_branch(client, genealogy_db, representation):
    """GET export?branch_name=main returns branch; nonexistent branch returns 404."""
    payload = _make_individual_payload(representation, 0)
    _save_population(client, [payload])
    _save_population(client, [payload], parent_id=1, generation_num=1)
    rv = client.get("/api/genealogy/export?branch_name=main")
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data["populations"]) == 2
    assert len(data["individuals"]) == 2
    rv404 = client.get("/api/genealogy/export?branch_name=nonexistent")
    assert rv404.status_code == 404
    assert "error" in rv404.get_json()


@pytest.mark.slow
def test_reset_genealogy(client, genealogy_db, representation):
    """POST reset clears all data; tree and stats are empty after."""
    payload = _make_individual_payload(representation, 0)
    _save_population(client, [payload])
    rv = client.post("/api/genealogy/reset")
    assert rv.status_code == 200
    assert rv.get_json().get("status") == "ok"
    tree_rv = client.get("/api/genealogy/tree")
    assert tree_rv.status_code == 200
    assert tree_rv.get_json()["nodes"] == []
    stats_rv = client.get("/api/genealogy/stats")
    assert stats_rv.status_code == 200
    s = stats_rv.get_json()
    assert s["total_populations"] == 0
    assert s["total_individuals"] == 0

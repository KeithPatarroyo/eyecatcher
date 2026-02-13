"""Tests for genealogy API (save/load population, tree, branches)."""

import pytest
from eyecatcher.substrate import create_random_dual_genome, dual_genome_to_json


@pytest.mark.slow
def test_save_population(client, genealogy_db, cppn_engine):
    """POST save-population with genomes returns population_id and individual_ids."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = 0

    rv = client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
            "description": "test",
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "population_id" in data
    assert data["population_id"] == 1
    assert data["individual_ids"] == [1]
    assert data["generation_num"] == 0


def test_save_population_empty_genomes(client, genealogy_db):
    """POST save-population without genomes returns 400."""
    rv = client.post(
        "/api/genealogy/save-population",
        json={"genomes": [], "generation_num": 0},
    )
    assert rv.status_code == 400
    assert "genomes" in rv.get_json().get("error", "").lower()


def test_load_population_not_found(client, genealogy_db):
    """GET load-population for missing id returns 404."""
    rv = client.get("/api/genealogy/load-population/99999")
    assert rv.status_code == 404
    assert "not found" in rv.get_json().get("error", "").lower()


@pytest.mark.slow
def test_save_and_load_population(client, genealogy_db, cppn_engine):
    """Save a population then load it by id; genomes round-trip."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=7
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = 7

    save_rv = client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )
    assert save_rv.status_code == 200
    pop_id = save_rv.get_json()["population_id"]

    load_rv = client.get(f"/api/genealogy/load-population/{pop_id}")
    assert load_rv.status_code == 200
    data = load_rv.get_json()
    assert data["population_id"] == pop_id
    assert data["generation_num"] == 0
    assert data["branch_name"] == "main"
    assert len(data["genomes"]) == 1
    assert data["genomes"][0]["key"] == 7
    assert "visual" in data["genomes"][0] and "time_signal" in data["genomes"][0]


def test_tree_empty(client, genealogy_db):
    """GET tree with no data returns empty nodes."""
    rv = client.get("/api/genealogy/tree")
    assert rv.status_code == 200
    assert rv.get_json()["nodes"] == []


@pytest.mark.slow
def test_tree_after_save(client, genealogy_db, cppn_engine):
    """GET tree after save returns one node."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = 0

    client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )

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
def test_export_genealogy_full(client, genealogy_db, cppn_engine):
    """GET export (no branch): full tree; populations, individuals, exported_at."""
    dual1 = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    dual2 = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=1
    )
    p1 = dual_genome_to_json(dual1)
    p2 = dual_genome_to_json(dual2)
    p1["key"] = 0
    p2["key"] = 1
    client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [p1, p2],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )
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
def test_export_genealogy_branch(client, genealogy_db, cppn_engine):
    """GET export?branch_name=main returns branch; nonexistent branch returns 404."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = 0
    client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )
    client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": 1,
            "generation_num": 1,
            "branch_name": "main",
        },
    )
    rv = client.get("/api/genealogy/export?branch_name=main")
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data["populations"]) == 2
    assert len(data["individuals"]) == 2
    rv404 = client.get("/api/genealogy/export?branch_name=nonexistent")
    assert rv404.status_code == 404
    assert "error" in rv404.get_json()


@pytest.mark.slow
def test_reset_genealogy(client, genealogy_db, cppn_engine):
    """POST reset clears all data; tree and stats are empty after."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = 0
    client.post(
        "/api/genealogy/save-population",
        json={
            "genomes": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )
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

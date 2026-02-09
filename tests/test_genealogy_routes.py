"""Tests for genealogy API (save/load population, tree, branches)."""


def test_save_population(client, genealogy_db, cppn_engine):
    """POST save-population with genomes returns population_id and individual_ids."""
    from eyecatcher.cppn_engine import create_random_dual_genome
    from eyecatcher.genome_serialization import dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
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


def test_save_and_load_population(client, genealogy_db, cppn_engine):
    """Save a population then load it by id; genomes round-trip."""
    from eyecatcher.cppn_engine import create_random_dual_genome
    from eyecatcher.genome_serialization import dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=7)
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


def test_tree_after_save(client, genealogy_db, cppn_engine):
    """GET tree after save returns one node."""
    from eyecatcher.cppn_engine import create_random_dual_genome
    from eyecatcher.genome_serialization import dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
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

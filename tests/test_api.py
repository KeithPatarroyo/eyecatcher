"""Tests for Flask API endpoints using test client."""

import pytest


def test_health(client):
    """GET /health returns 200."""
    rv = client.get("/health")
    assert rv.status_code == 200


def test_api_random(client):
    """POST /api/random with size returns genomes."""
    rv = client.post("/api/random", json={"size": 3})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "genomes" in data
    assert len(data["genomes"]) == 3
    for g in data["genomes"]:
        assert "key" in g
        assert "visual" in g
        assert "time_signal" in g


@pytest.mark.slow
def test_api_compile(client):
    """POST /api/compile with genomes returns shaders."""
    # Get genomes first
    rv = client.post("/api/random", json={"size": 2})
    assert rv.status_code == 200
    genomes = rv.get_json()["genomes"]
    rv = client.post("/api/compile", json={"genomes": genomes})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "shaders" in data
    assert len(data["shaders"]) == 2
    for s in data["shaders"]:
        assert "shader" in s
        assert "void main()" in s["shader"]


def test_api_breed(client):
    """POST /api/breed with parents returns children."""
    rv = client.post("/api/random", json={"size": 2})
    assert rv.status_code == 200
    genomes = rv.get_json()["genomes"]
    parents = [{"genome": g, "clicks": 1} for g in genomes]
    rv = client.post(
        "/api/breed",
        json={"parents": parents, "population_size": 4},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "children" in data
    assert len(data["children"]) == 4


def test_api_breed_without_genealogy(client, cppn_engine):
    """Breed without parent_population_id returns children only, no population_id."""
    from eyecatcher.evolution import create_random_dual_genome, dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0
    parents = [{"genome": genome, "clicks": 0}]
    rv = client.post(
        "/api/breed",
        json={"parents": parents, "population_size": 2},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "children" in data
    assert len(data["children"]) == 2
    assert "population_id" not in data


def test_api_breed_missing_parents(client):
    """POST /api/breed without parents returns 400."""
    rv = client.post("/api/breed", json={})
    assert rv.status_code == 400
    assert "parents" in rv.get_json().get("error", "").lower()


def test_api_breed_empty_parents(client):
    """POST /api/breed with empty parents returns 400."""
    rv = client.post("/api/breed", json={"parents": []})
    assert rv.status_code == 400


def test_api_breed_malformed_parents(client):
    """POST /api/breed with invalid genome in parents returns 400."""
    rv = client.post(
        "/api/breed",
        json={"parents": [{"genome": "not a genome", "clicks": 0}]},
    )
    assert rv.status_code == 400
    assert "no valid parents" in rv.get_json().get("error", "").lower()


@pytest.mark.slow
def test_api_breed_with_genealogy(client, genealogy_db, cppn_engine):
    """Breed with parent_population_id saves to genealogy and returns population_id."""
    from eyecatcher.evolution import create_random_dual_genome, dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    payload = dual_genome_to_json(dual)
    payload["key"] = 0
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
    parents = [{"genome": payload, "clicks": 1}]
    breed_rv = client.post(
        "/api/breed",
        json={
            "parents": parents,
            "population_size": 2,
            "parent_population_id": pop_id,
            "generation_num": 1,
            "branch_name": "main",
        },
    )
    assert breed_rv.status_code == 200
    data = breed_rv.get_json()
    assert "children" in data
    assert "population_id" in data
    assert data["population_id"] != pop_id


@pytest.mark.slow
def test_api_save(client, cppn_engine):
    """POST /api/save with genome returns id, status, and downloads."""
    from eyecatcher.evolution import create_random_dual_genome, dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0
    rv = client.post("/api/save", json={"genome": genome})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("id") == 0
    assert data.get("status") == "saved"
    assert "downloads" in data
    assert len(data["downloads"]) == 1
    assert data["downloads"][0].get("filename") == "pattern_0.zip"
    assert "content_base64" in data["downloads"][0]


@pytest.mark.slow
def test_save_download_structure(client, cppn_engine):
    """Save returns downloads[0] with .zip filename and non-empty content_base64."""
    from eyecatcher.evolution import create_random_dual_genome, dual_genome_to_json

    dual = create_random_dual_genome(cppn_engine, genome_id=0)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0
    rv = client.post("/api/save", json={"genome": genome})
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data["downloads"]) >= 1
    d = data["downloads"][0]
    assert d.get("filename", "").endswith(".zip")
    assert isinstance(d.get("content_base64"), str)
    assert len(d["content_base64"]) > 0


def test_api_save_missing_genome(client):
    """POST /api/save without genome returns 400."""
    rv = client.post("/api/save", json={})
    assert rv.status_code == 400
    assert "genome" in rv.get_json().get("error", "").lower()


def test_api_time_output(client):
    """POST /api/time-output with genome returns timeOutput and inputs."""
    rv = client.post("/api/random", json={"size": 1})
    assert rv.status_code == 200
    genome = rv.get_json()["genomes"][0]
    rv = client.post(
        "/api/time-output",
        json={
            "genome": genome,
            "time": 0.5,
            "mouseSpeed": 0,
            "mouseDist": 0,
            "activity": 0,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "timeOutput" in data
    assert isinstance(data["timeOutput"], (int, float))
    assert "inputs" in data
    assert data["inputs"]["rawTime"] == 0.5


def test_api_time_output_missing_genome(client):
    """POST /api/time-output without genome returns 400."""
    rv = client.post("/api/time-output", json={})
    assert rv.status_code == 400
    assert "genome" in rv.get_json().get("error", "").lower()


def test_api_network(client):
    """POST /api/network with genome returns nodes and connections."""
    rv = client.post("/api/random", json={"size": 1})
    assert rv.status_code == 200
    genome = rv.get_json()["genomes"][0]
    rv = client.post("/api/network", json={"genome": genome})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("status") == "success"
    assert "nodes" in data
    assert "connections" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["connections"], list)


def test_api_network_missing_genome(client):
    """POST /api/network without genome returns 400."""
    rv = client.post("/api/network", json={})
    assert rv.status_code == 400
    assert "genome" in rv.get_json().get("error", "").lower()


def test_api_error_response_shape(client):
    """Error responses have exactly one key 'error' with a string value."""
    rv = client.post("/api/breed", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert list(data.keys()) == ["error"]
    assert isinstance(data["error"], str)
    assert len(data["error"]) > 0


def test_api_adjust_weight(client, cppn_engine):
    """POST /api/adjust-weight with valid payload returns shader and genome."""
    from conftest import minimal_dual_genome_one_hidden_visual
    from eyecatcher.evolution import dual_genome_to_json

    dual = minimal_dual_genome_one_hidden_visual(cppn_engine)
    genome = dual_genome_to_json(dual)
    genome["key"] = 0
    net_rv = client.post("/api/network", json={"genome": genome})
    assert net_rv.status_code == 200
    conns = [
        c
        for c in net_rv.get_json().get("connections", [])
        if c.get("network") == "visual"
    ]
    assert len(conns) >= 1, "minimal genome has visual connections"
    c = conns[0]
    source = c.get("source")
    target = c.get("target")
    assert source and target, "connection has source and target"
    rv = client.post(
        "/api/adjust-weight",
        json={
            "genome": genome,
            "network": "visual",
            "source": source,
            "target": target,
            "weight": 0.5,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("status") == "success"
    assert "shader" in data
    assert "genome" in data

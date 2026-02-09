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


def test_api_adjust_weight(client):
    """POST /api/adjust-weight with valid payload returns shader and genome."""
    rv = client.post("/api/random", json={"size": 1})
    assert rv.status_code == 200
    genome = rv.get_json()["genomes"][0]
    net_rv = client.post("/api/network", json={"genome": genome})
    assert net_rv.status_code == 200
    conns = [
        c
        for c in net_rv.get_json().get("connections", [])
        if c.get("network") == "visual"
    ]
    if not conns:
        pytest.skip("no visual connections in network")
    c = conns[0]
    source = c.get("source")
    target = c.get("target")
    if not source or not target:
        pytest.skip("connection missing source/target")
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

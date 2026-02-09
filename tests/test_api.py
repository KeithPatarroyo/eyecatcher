"""Tests for Flask API endpoints using test client."""
import pytest

from eyecatcher.server import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


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

"""Tests for Flask API endpoints using test client."""

import pytest
from eyecatcher.genome import create_random_dual_genome, dual_genome_to_json


def _random_individuals(client, size):
    """POST /api/random and return individuals list."""
    rv = client.post("/api/random", json={"size": size})
    assert rv.status_code == 200
    return rv.get_json()["individuals"]


def _make_dual_payload(representation, key=0):
    """Build dual genome JSON with key for API payloads."""
    dual = create_random_dual_genome(
        representation.config, representation.time_config, genome_id=key
    )
    payload = dual_genome_to_json(dual)
    payload["key"] = key
    return payload


def test_health(client):
    """GET /health returns 200."""
    rv = client.get("/health")
    assert rv.status_code == 200


def test_api_random(client):
    """POST /api/random with size returns individuals and output_type."""
    rv = client.post("/api/random", json={"size": 3})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "individuals" in data
    assert "output_type" in data
    assert len(data["individuals"]) == 3
    for g in data["individuals"]:
        assert "key" in g
        assert "visual" in g
        assert "time_signal" in g


def test_api_express(client):
    """POST /api/express returns results (field or grid per representation)."""
    individuals = _random_individuals(client, 2)
    rv = client.post("/api/express", json={"individuals": individuals})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "results" in data
    assert "output_type" in data
    assert len(data["results"]) == 2
    for r in data["results"]:
        assert "id" in r
        assert r["output_type"] == data["output_type"]
    if data["output_type"] == "field":
        assert "rule" in data["results"][0]
    elif data["output_type"] == "grid":
        assert "image" in data["results"][0]
        assert data["results"][0]["image"].startswith("data:image/png;base64,")


@pytest.mark.slow
def test_api_develop(client):
    """POST /api/develop with individuals returns rules."""
    individuals = _random_individuals(client, 2)
    rv = client.post("/api/develop", json={"individuals": individuals})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "rules" in data
    assert len(data["rules"]) == 2
    for r in data["rules"]:
        assert "rule" in r
        assert "void main()" in r["rule"]


def test_api_evolve(client):
    """POST /api/evolve with parents returns children."""
    individuals = _random_individuals(client, 2)
    parents = [{"individual": g, "fitness": 1} for g in individuals]
    rv = client.post(
        "/api/evolve",
        json={"parents": parents, "population_size": 4},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "children" in data
    assert len(data["children"]) == 4


def test_api_evolve_without_genealogy(client, representation):
    """Evolve without parent_population_id returns children only, no population_id."""
    ind_json = _make_dual_payload(representation, 0)
    parents = [{"individual": ind_json, "fitness": 0}]
    rv = client.post(
        "/api/evolve",
        json={"parents": parents, "population_size": 2},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "children" in data
    assert len(data["children"]) == 2
    assert "population_id" not in data


@pytest.mark.parametrize(
    "payload,error_substring",
    [
        ({}, "parents"),
        ({"parents": []}, None),
        (
            {"parents": [{"individual": "not an individual", "fitness": 0}]},
            "no valid parents",
        ),
    ],
    ids=["missing_parents", "empty_parents", "malformed_parents"],
)
def test_api_evolve_bad_request(client, payload, error_substring):
    """POST /api/evolve with missing/empty/malformed parents returns 400."""
    rv = client.post("/api/evolve", json=payload)
    assert rv.status_code == 400
    if error_substring:
        assert error_substring in rv.get_json().get("error", "").lower()


@pytest.mark.slow
def test_api_evolve_with_genealogy(client, genealogy_db, representation):
    """Evolve with parent_population_id saves to genealogy and returns population_id."""
    payload = _make_dual_payload(representation, 0)
    save_rv = client.post(
        "/api/genealogy/save-population",
        json={
            "individuals": [payload],
            "parent_id": None,
            "generation_num": 0,
            "branch_name": "main",
        },
    )
    assert save_rv.status_code == 200
    pop_id = save_rv.get_json()["population_id"]
    parents = [{"individual": payload, "fitness": 1}]
    evolve_rv = client.post(
        "/api/evolve",
        json={
            "parents": parents,
            "population_size": 2,
            "parent_population_id": pop_id,
            "generation_num": 1,
            "branch_name": "main",
        },
    )
    assert evolve_rv.status_code == 200
    data = evolve_rv.get_json()
    assert "children" in data
    assert "population_id" in data
    assert data["population_id"] != pop_id


@pytest.mark.slow
def test_api_save(client, representation):
    """POST /api/save with individual returns id, status, and downloads."""
    ind_json = _make_dual_payload(representation, 0)
    rv = client.post("/api/save", json={"individual": ind_json})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("id") == 0
    assert data.get("status") == "saved"
    assert "downloads" in data
    assert len(data["downloads"]) == 1
    assert data["downloads"][0].get("filename") == "pattern_0.zip"
    assert "content_base64" in data["downloads"][0]


@pytest.mark.slow
def test_save_download_structure(client, representation):
    """Save returns downloads[0] with .zip filename and non-empty content_base64."""
    ind_json = _make_dual_payload(representation, 0)
    rv = client.post("/api/save", json={"individual": ind_json})
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data["downloads"]) >= 1
    d = data["downloads"][0]
    assert d.get("filename", "").endswith(".zip")
    assert isinstance(d.get("content_base64"), str)
    assert len(d["content_base64"]) > 0


def test_api_time_output(client):
    """POST /api/time-output with individual returns timeOutput and inputs."""
    individuals = _random_individuals(client, 1)
    ind = individuals[0]
    rv = client.post(
        "/api/time-output",
        json={
            "individual": ind,
            "raw_time": 0.5,
            "mouse_speed": 0,
            "mouse_dist": 0,
            "activity": 0,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "timeOutput" in data
    assert isinstance(data["timeOutput"], (int, float))
    assert "inputs" in data
    assert data["inputs"]["raw_time"] == 0.5


def test_api_network(client):
    """POST /api/network with individual returns nodes and connections."""
    individuals = _random_individuals(client, 1)
    ind = individuals[0]
    rv = client.post("/api/network", json={"individual": ind})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("status") == "success"
    assert "nodes" in data
    assert "connections" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["connections"], list)


@pytest.mark.parametrize(
    "endpoint,payload,error_key",
    [
        ("/api/save", {}, "individual"),
        ("/api/time-output", {}, "individual"),
        ("/api/network", {}, "individual"),
    ],
    ids=["save_missing_genome", "time_output_missing", "network_missing"],
)
def test_api_missing_individual_400(client, endpoint, payload, error_key):
    """POST without required individual returns 400."""
    rv = client.post(endpoint, json=payload)
    assert rv.status_code == 400
    assert error_key in rv.get_json().get("error", "").lower()


def test_api_error_response_shape(client):
    """Error responses have exactly one key 'error' with a string value."""
    rv = client.post("/api/evolve", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert list(data.keys()) == ["error"]
    assert isinstance(data["error"], str)
    assert len(data["error"]) > 0


def test_api_adjust_weight(client, representation):
    """POST /api/adjust-weight with valid payload returns rule and individual."""
    from tests.conftest import minimal_dual_genome_one_hidden_visual

    dual = minimal_dual_genome_one_hidden_visual(representation)
    ind_json = dual_genome_to_json(dual)
    ind_json["key"] = 0
    net_rv = client.post("/api/network", json={"individual": ind_json})
    assert net_rv.status_code == 200
    conns = [
        c
        for c in net_rv.get_json().get("connections", [])
        if c.get("network") == "visual"
    ]
    assert len(conns) >= 1, "minimal individual has visual connections"
    c = conns[0]
    source = c.get("source")
    target = c.get("target")
    assert source and target, "connection has source and target"
    rv = client.post(
        "/api/adjust-weight",
        json={
            "individual": ind_json,
            "network": "visual",
            "source": source,
            "target": target,
            "weight": 0.5,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("status") == "success"
    assert "rule" in data
    assert "individual" in data


def test_api_config_get(client):
    """GET /api/config returns representation_id, output_type, available_representation_ids."""  # noqa: E501
    rv = client.get("/api/config")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "representation_id" in data
    assert "output_type" in data
    assert "available_representation_ids" in data
    assert isinstance(data["available_representation_ids"], list)
    assert data["representation_id"] in data["available_representation_ids"]


def test_api_config_patch_representation_id(client):
    """PATCH /api/config representation_id; next GET and /api/random use it."""
    rv = client.get("/api/config")
    assert rv.status_code == 200
    initial_id = rv.get_json()["representation_id"]

    rv = client.patch(
        "/api/config",
        json={"representation_id": "ca"},
        headers={"Content-Type": "application/json"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["representation_id"] == "ca"
    assert data["output_type"] == "grid"

    rv = client.get("/api/config")
    assert rv.status_code == 200
    assert rv.get_json()["representation_id"] == "ca"

    rv = client.post("/api/random", json={"size": 1})
    assert rv.status_code == 200
    assert rv.get_json()["output_type"] == "grid"
    individuals = rv.get_json()["individuals"]
    assert len(individuals) == 1
    assert "grid" in individuals[0]

    # Restore so other tests see default representation
    client.patch(
        "/api/config",
        json={"representation_id": initial_id},
        headers={"Content-Type": "application/json"},
    )


def test_api_config_patch_invalid_representation_id(client):
    """PATCH /api/config with unknown representation_id returns 400."""
    rv = client.patch(
        "/api/config",
        json={"representation_id": "nonexistent"},
        headers={"Content-Type": "application/json"},
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data
    assert (
        "nonexistent" in data["error"].lower() or "available" in data["error"].lower()
    )

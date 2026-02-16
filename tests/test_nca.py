"""Tests for NCA (Neural Cellular Automata) representation.

NCA uses NEAT to evolve the update-rule network (14 inputs -> 4 state-delta outputs).
"""

import os

import neat
import pytest
from eyecatcher.evolution import produce_next_generation
from eyecatcher.evolution.fitness import get_fitness
from eyecatcher.representation import get_representation
from eyecatcher.representation.nca import DEFAULT_GRID_SIZE, NCARepresentation

from tests.representation_test_helpers import assert_representation_protocol_compliance


@pytest.fixture
def nca_representation():
    """NCARepresentation instance for tests."""
    return NCARepresentation()


@pytest.fixture
def nca_genome(nca_representation):
    """Random NCA genome (NEAT DefaultGenome)."""
    return nca_representation.create_random(key=42)


def test_nca_id_and_output_type(nca_representation):
    assert nca_representation.id == "nca"
    assert nca_representation.output_type == "grid"


def test_nca_create_random_returns_neat_genome(nca_representation):
    ind = nca_representation.create_random(key=1)
    assert isinstance(ind, neat.DefaultGenome)
    assert ind.key == 1
    assert hasattr(ind, "nodes") and hasattr(ind, "connections")


def test_nca_mutate_returns_new_genome(nca_representation, nca_genome):
    mutated = nca_representation.mutate(nca_genome, key=99)
    assert isinstance(mutated, neat.DefaultGenome)
    assert mutated.key == 99


def test_nca_crossover_returns_valid_genome(nca_representation):
    a = nca_representation.create_random(key=1)
    b = nca_representation.create_random(key=2)
    child = nca_representation.crossover(a, b, key=3)
    assert isinstance(child, neat.DefaultGenome)
    assert child.key == 3


def test_nca_express_returns_grid_output(nca_representation, nca_genome):
    out = nca_representation.express(nca_genome, {})
    assert out.output_type == "grid"
    assert hasattr(out.data, "shape")
    assert out.data.shape == (DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE, 3)


def test_nca_develop_returns_glsl_string(nca_representation, nca_genome):
    glsl = nca_representation.develop(nca_genome)
    assert glsl is not None
    assert "#version 300 es" in glsl
    assert "void main()" in glsl
    assert "u_state" in glsl
    assert "u_raw_time" in glsl
    assert "getState" in glsl
    assert "fragColor" in glsl


def test_nca_to_json_from_json_roundtrip(nca_representation, nca_genome):
    data = nca_representation.to_json(nca_genome)
    assert "key" in data and "nodes" in data and "connections" in data
    restored = nca_representation.from_json(data)
    assert restored.key == nca_genome.key


def test_nca_serialize_output_includes_rule(nca_representation, nca_genome):
    out = nca_representation.express(nca_genome, {})
    result = nca_representation.serialize_output(out, nca_genome)
    assert "rule" in result
    assert "grid" in result
    assert "image" in result
    assert "#version 300 es" in result["rule"]


def test_nca_get_representation_nca():
    rep = get_representation("nca")
    assert rep.id == "nca"
    ind = rep.create_random(key=0)
    out = rep.express(ind, {})
    assert out.output_type == "grid"
    assert out.data.shape == (DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE, 3)


def test_nca_protocol_compliance(nca_representation):
    assert_representation_protocol_compliance(nca_representation)


def test_nca_get_network_types(nca_representation):
    types = nca_representation.get_network_types()
    assert types == ("nca_update",)


def test_nca_get_network_data(nca_representation, nca_genome):
    result = nca_representation.get_network_data(nca_genome)
    assert result is not None
    assert "nodes" in result and "connections" in result
    assert isinstance(result["nodes"], list)
    assert isinstance(result["connections"], list)
    node_ids = {n["id"] for n in result["nodes"]}
    assert any("input" in n["id"] for n in result["nodes"])
    assert any("output" in n["id"] for n in result["nodes"])
    for conn in result["connections"]:
        assert conn["source"] in node_ids and conn["target"] in node_ids
        assert "weight" in conn and conn.get("network") == "nca_update"


def test_nca_adjust_weight(nca_representation, nca_genome):
    result = nca_representation.get_network_data(nca_genome)
    conns = [c for c in result["connections"] if c.get("network") == "nca_update"]
    if not conns:
        pytest.skip("no connections in random genome")
    c = conns[0]
    out = nca_representation.adjust_weight(
        nca_genome,
        "nca_update",
        c["source"],
        c["target"],
        0.5,
    )
    assert out is not None
    assert "rule" in out and "individual" in out
    assert "#version 300 es" in out["rule"]


def test_nca_develop_returns_valid_glsl():
    """Assembled NCA step shader contains required GLSL elements."""
    rep = NCARepresentation()
    genome = rep.create_random(key=1)
    glsl = rep.develop(genome)
    assert "#version 300 es" in glsl
    assert "precision highp float" in glsl
    assert "uniform sampler2D u_state" in glsl
    assert "uniform vec2 u_texelSize" in glsl
    assert "in vec2 vUV" in glsl
    assert "out vec4 fragColor" in glsl
    assert "void main()" in glsl
    assert "getState" in glsl


def test_nca_smoke_experiment_config_and_evolution():
    """Smoke test: NCA preset loads and one evolution step runs."""
    from eyecatcher import experiment

    old_val = os.environ.get("EXPERIMENT_CONFIG")
    try:
        os.environ["EXPERIMENT_CONFIG"] = "nca"
        rep = experiment.get_configured_representation()
        assert rep.id == "nca"

        population = [rep.create_random(key=i) for i in range(4)]
        fitness_fn = get_fitness("nca_alive_count")
        assert fitness_fn is not None
        scores = [(ind, fitness_fn(ind, rep)) for ind in population]
        scores.sort(key=lambda x: x[1], reverse=True)
        parents = [ind for ind, _ in scores[:4]]
        parents_data = [{"genome": rep.to_json(p), "fitness": 1} for p in parents]
        children = produce_next_generation(
            rep,
            parents_data,
            population_size=4,
            elitism=True,
            crossover_probability=experiment.get_crossover_probability(),
        )
        assert len(children) == 4
        next_pop = [rep.from_json(c) for c in children]
        for ind in next_pop:
            out = rep.express(ind, {})
            assert out.data.shape == (DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE, 3)
    finally:
        if old_val is None:
            os.environ.pop("EXPERIMENT_CONFIG", None)
        else:
            os.environ["EXPERIMENT_CONFIG"] = old_val

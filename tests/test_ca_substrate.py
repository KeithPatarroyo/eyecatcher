"""Tests for the Conway's Game of Life (CA) substrate."""

import numpy as np
import pytest
from eyecatcher.substrate import (
    ConwayGenome,
    ElementaryCASubstrate,
    SubstrateOutput,
    get_substrate,
)
from eyecatcher.substrate.ca import DEFAULT_GRID_SIZE

from tests.substrate_test_helpers import assert_substrate_protocol_compliance


@pytest.fixture
def ca_substrate():
    return ElementaryCASubstrate(grid_size=64, gol_steps=32)


def test_ca_substrate_id_and_output_type(ca_substrate):
    assert ca_substrate.id == "ca"
    assert ca_substrate.output_type == "grid"


def test_create_random_returns_conway_genome(ca_substrate):
    ind = ca_substrate.create_random(key=1)
    assert isinstance(ind, ConwayGenome)
    assert ind.grid.shape == (64, 64)
    assert ind.grid.dtype == np.uint8
    assert ind.grid.min() in (0, 1) and ind.grid.max() in (0, 1)
    assert ind.key == 1


def test_mutate_returns_new_conway_genome(ca_substrate):
    ind = ConwayGenome(grid=np.zeros((64, 64), dtype=np.uint8), key=0)
    ind.grid[10, 10] = 1
    mutated = ca_substrate.mutate(ind, key=1)
    assert isinstance(mutated, ConwayGenome)
    assert mutated.key == 1
    assert mutated.grid.shape == (64, 64)
    diff = np.sum(mutated.grid != ind.grid)
    assert diff == 1, "mutate flips exactly one cell"


def test_crossover_returns_valid_conway_genome(ca_substrate):
    a = ConwayGenome(grid=np.zeros((64, 64), dtype=np.uint8), key=0)
    b = ConwayGenome(grid=np.ones((64, 64), dtype=np.uint8), key=1)
    child = ca_substrate.crossover(a, b, key=2)
    assert isinstance(child, ConwayGenome)
    assert child.key == 2
    assert child.grid.shape == (64, 64)
    assert child.grid.dtype == np.uint8


def test_evaluate_returns_grid_output(ca_substrate):
    ind = ca_substrate.create_random(key=0)
    out = ca_substrate.evaluate(ind, {})
    assert isinstance(out, SubstrateOutput)
    assert out.output_type == "grid"
    assert out.data.shape == (64, 64, 3)
    assert out.data.dtype == np.uint8
    assert out.data.min() in (0, 255) and out.data.max() in (0, 255)


def test_evaluate_respects_kwargs(ca_substrate):
    ind = ca_substrate.create_random(key=0)
    out = ca_substrate.evaluate(ind, {}, gol_steps=8)
    assert out.output_type == "grid"
    assert out.data.shape == (64, 64, 3)


def test_compile_to_shader_returns_gol_glsl(ca_substrate):
    ind = ca_substrate.create_random(key=0)
    glsl = ca_substrate.compile_to_shader(ind)
    assert glsl is not None
    assert "u_state" in glsl
    assert "u_texelSize" in glsl
    assert "void main()" in glsl
    assert "uRule" not in glsl
    assert "uGeneration" not in glsl


def test_to_json_from_json_roundtrip(ca_substrate):
    ind = ca_substrate.create_random(key=42)
    data = ca_substrate.to_json(ind)
    assert "grid" in data
    assert data["key"] == 42
    assert len(data["grid"]) == 64
    assert len(data["grid"][0]) == 64
    restored = ca_substrate.from_json(data)
    np.testing.assert_array_equal(restored.grid, ind.grid)
    assert restored.key == ind.key


def test_get_substrate_ca():
    sub = get_substrate("ca", grid_size=32, gol_steps=16)
    assert sub.id == "ca"
    ind = sub.create_random(key=0)
    out = sub.evaluate(ind, {})
    assert out.output_type == "grid"
    assert out.data.shape == (32, 32, 3)


def test_ca_protocol_compliance(ca_substrate):
    """CA substrate satisfies the generic protocol compliance helper."""
    assert_substrate_protocol_compliance(ca_substrate)


def test_serialize_individual_extra_includes_grid(ca_substrate):
    ind = ca_substrate.create_random(key=0)
    extra = ca_substrate.serialize_individual_extra(ind)
    assert "grid" in extra
    assert len(extra["grid"]) == DEFAULT_GRID_SIZE
    assert len(extra["grid"][0]) == DEFAULT_GRID_SIZE

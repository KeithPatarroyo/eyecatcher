"""Tests for the elementary CA substrate (substrate protocol)."""

import numpy as np
import pytest
from eyecatcher.substrate import (
    CARule,
    ElementaryCASubstrate,
    SubstrateOutput,
    get_substrate,
)


@pytest.fixture
def ca_substrate():
    return ElementaryCASubstrate(width=64, generations=32)


def test_ca_substrate_id_and_output_type(ca_substrate):
    assert ca_substrate.id == "ca"
    assert ca_substrate.output_type == "grid"


def test_create_random_returns_carule(ca_substrate):
    ind = ca_substrate.create_random(key=1)
    assert isinstance(ind, CARule)
    assert 0 <= ind.rule <= 255
    assert ind.key == 1


def test_mutate_returns_new_carule(ca_substrate):
    ind = CARule(rule=30, key=0)
    mutated = ca_substrate.mutate(ind, key=1)
    assert isinstance(mutated, CARule)
    assert mutated.key == 1
    # Mutation flips one bit, so rule may or may not equal 30
    assert 0 <= mutated.rule <= 255


def test_crossover_returns_valid_carule(ca_substrate):
    a = CARule(rule=30, key=0)
    b = CARule(rule=90, key=1)
    child = ca_substrate.crossover(a, b, key=2)
    assert isinstance(child, CARule)
    assert child.key == 2
    assert 0 <= child.rule <= 255


def test_evaluate_returns_grid_output(ca_substrate):
    ind = CARule(rule=30, key=0)
    out = ca_substrate.evaluate(ind, {})
    assert isinstance(out, SubstrateOutput)
    assert out.output_type == "grid"
    assert out.data.shape == (32, 64, 3)
    assert out.data.dtype == np.uint8
    assert out.data.min() in (0, 255) and out.data.max() in (0, 255)


def test_evaluate_respects_kwargs(ca_substrate):
    ind = CARule(rule=110, key=0)
    out = ca_substrate.evaluate(ind, {}, width=32, generations=16)
    assert out.output_type == "grid"
    assert out.data.shape == (16, 32, 3)


def test_compile_to_shader_returns_glsl(ca_substrate):
    ind = CARule(rule=30, key=0)
    glsl = ca_substrate.compile_to_shader(ind)
    assert glsl is not None
    assert "uRule" in glsl
    assert "uGeneration" in glsl
    assert "void main()" in glsl


def test_to_json_from_json_roundtrip(ca_substrate):
    ind = CARule(rule=150, key=42)
    data = ca_substrate.to_json(ind)
    assert data["rule"] == 150
    assert data["key"] == 42
    restored = ca_substrate.from_json(data)
    assert restored.rule == ind.rule
    assert restored.key == ind.key


def test_get_substrate_ca():
    sub = get_substrate("ca", width=32, generations=16)
    assert sub.id == "ca"
    ind = sub.create_random(key=0)
    out = sub.evaluate(ind, {})
    assert out.output_type == "grid"
    assert out.data.shape == (16, 32, 3)

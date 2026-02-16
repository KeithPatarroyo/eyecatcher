"""
Tests for the canonical activation registry: GLSL block and JS sync.
"""

from eyecatcher.glsl.activation_registry import (
    get_activation_names_sorted,
    get_glsl_block,
)


def test_activation_names_non_empty():
    names = get_activation_names_sorted()
    assert len(names) >= 10
    assert "identity" in names
    assert "sigmoid" in names


def test_glsl_block_contains_custom_activations():
    block = get_glsl_block()
    assert "sigmoid" in block
    assert "identity" in block
    assert "float " in block

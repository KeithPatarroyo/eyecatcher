"""
Tests for the canonical activation registry: GLSL block and JS sync.
"""

from eyecatcher.glsl.activation_registry import (
    build_shader_preamble,
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


def test_build_shader_preamble_includes_version_and_middle():
    middle = "in vec2 vUV;\nout vec4 fragColor;\n"
    preamble = build_shader_preamble(middle)
    assert preamble.startswith("#version 300 es")
    assert "precision highp float" in preamble
    assert "in vec2 vUV;" in preamble
    assert "out vec4 fragColor;" in preamble
    assert "sigmoid" in preamble  # from get_glsl_block()

"""
Tests for the canonical activation registry: GLSL block and JS sync.
"""

import re

from eyecatcher.glsl.activation_registry import (
    get_activation_names,
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


def test_js_activations_match_python_registry():
    """JS ACTIVATIONS keys must match Python registry (single source of truth)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    js_path = root / "static" / "js" / "evaluation" / "cppn_evaluator.js"
    content = js_path.read_text(encoding="utf-8")
    # Extract keys from "var ACTIVATIONS = { key: function ... }"
    keys = re.findall(r"(\w+):\s*function\s*\(", content)
    js_set = set(keys)
    py_set = get_activation_names()
    assert js_set == py_set, (
        f"JS ACTIVATIONS keys must match Python registry. "
        f"Only in JS: {js_set - py_set}. Only in Python: {py_set - js_set}."
    )

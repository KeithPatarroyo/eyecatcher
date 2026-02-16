"""
Canonical registry of NEAT activation functions: name, GLSL body, and built-in flag.

Single source of truth for GLSL compilation and JS validation.
Add new activations here; GLSL block and name lists are derived from this registry.
"""

from typing import NamedTuple


class _ActivationEntry(NamedTuple):
    """One activation: name, GLSL body (empty if built-in), is_builtin."""

    name: str
    glsl_body: str
    is_builtin: bool


# Built-ins: tanh, sin, cos, abs, exp, log — GLSL provides them; no body needed.
# Custom: sigmoid, gauss, relu, square, cube, identity, clamped, hat, inv.
_ACTIVATIONS: list[_ActivationEntry] = [
    _ActivationEntry(
        "sigmoid",
        "float sigmoid(float x) {\n    return 1.0 / (1.0 + exp(-x));\n}",
        False,
    ),
    _ActivationEntry("tanh", "", True),
    _ActivationEntry("sin", "", True),
    _ActivationEntry("cos", "", True),
    _ActivationEntry(
        "gauss", "float gauss(float x) {\n    return exp(-x * x);\n}", False
    ),
    _ActivationEntry(
        "relu", "float relu(float x) {\n    return max(0.0, x);\n}", False
    ),
    _ActivationEntry("abs", "", True),
    _ActivationEntry("square", "float square(float x) {\n    return x * x;\n}", False),
    _ActivationEntry("cube", "float cube(float x) {\n    return x * x * x;\n}", False),
    _ActivationEntry("identity", "float identity(float x) {\n    return x;\n}", False),
    _ActivationEntry(
        "clamped", "float clamped(float x) {\n    return clamp(x, -1.0, 1.0);\n}", False
    ),
    _ActivationEntry("exp", "", True),
    _ActivationEntry(
        "hat", "float hat(float x) {\n    return max(0.0, 1.0 - abs(x));\n}", False
    ),
    _ActivationEntry(
        "inv",
        "float inv(float x) {\n"
        "    if (abs(x) < 0.001) return 0.0;\n    return 1.0 / x;\n}",
        False,
    ),
    _ActivationEntry("log", "", True),
]


def get_activation_names() -> set[str]:
    """Return the set of valid NEAT/GLSL activation names (for compiler fallback)."""
    return {e.name for e in _ACTIVATIONS}


def get_glsl_block() -> str:
    """Build the GLSL activation block from the registry (custom functions only)."""
    lines = ["// Activation functions"]
    for entry in _ACTIVATIONS:
        if not entry.is_builtin and entry.glsl_body:
            lines.append(entry.glsl_body)
    return "\n".join(lines)


def build_shader_preamble(middle: str) -> str:
    """Build shared shader header: version, precision, middle, activation block."""
    return f"""#version 300 es
precision highp float;
{middle}
{get_glsl_block()}
"""


def get_activation_names_sorted() -> list[str]:
    """Return activation names in registry order (for tests and codegen)."""
    return [e.name for e in _ACTIVATIONS]

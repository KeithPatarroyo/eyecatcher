"""
GLSL naming and input mapping for the rule assembler.

Maps signals to variable/uniform names used in generated code.
Domain-agnostic Signal type is used; this module encapsulates GLSL naming convention.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..signals.sensory_system import Signal


def glsl_var_name(signal: Signal) -> str:
    """Return the GLSL varying/variable name for this signal (e.g. v_x)."""
    return f"v_{signal.id}"


def glsl_uniform_name(signal: Signal) -> str:
    """Return the GLSL uniform name for this signal if toggleable, else empty string."""
    if not signal.is_spatial and not signal.is_constant:
        return f"u_{signal.id}"
    return ""


def build_glsl_input_map(signals: Sequence[Signal]) -> dict[int, str]:
    """Map NEAT negative node IDs to GLSL variable names.

    First signal gets the most-negative ID.
    """
    n = len(signals)
    return {-n + i: glsl_var_name(signals[i]) for i in range(n)}

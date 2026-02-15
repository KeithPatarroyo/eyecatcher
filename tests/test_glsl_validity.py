"""Tests that generated GLSL is valid: all used variables are declared.

Catches regressions like undeclared v_mouse_x or mouse_x_base, or redefinition
of v_* (e.g. shared time/visual signals), that would fail at WebGL compile time.
"""

import re
from collections import Counter

from eyecatcher.glsl.input_map import glsl_uniform_name
from eyecatcher.representation import SingleCPPNRepresentation
from eyecatcher.signals import catalog


def _declared_v_identifiers(glsl: str) -> set[str]:
    """Set of v_* identifiers that are declared (float v_foo or float v_foo = ...)."""
    return set(re.findall(r"float\s+(v_\w+)", glsl))


def _v_redefinitions(glsl: str) -> list[str]:
    """List of v_* identifiers that are declared more than once (redefinition)."""
    declarations = re.findall(r"float\s+(v_\w+)", glsl)
    return [v for v, count in Counter(declarations).items() if count > 1]


def _declared_base_identifiers(glsl: str) -> set[str]:
    """Set of *_base identifiers that are defined (foo_base = ...)."""
    return set(re.findall(r"(\w+_base)\s*=", glsl))


def _used_v_identifiers(glsl: str) -> set[str]:
    """v_* identifiers that appear as words in the shader (use or declaration)."""
    return set(re.findall(r"\b(v_\w+)\b", glsl))


def _used_base_identifiers(glsl: str) -> set[str]:
    """Set of *_base identifiers that appear as words in the shader."""
    return set(re.findall(r"\b(\w+_base)\b", glsl))


def _assert_all_used_vars_declared(glsl: str) -> None:
    """Raise AssertionError if any v_* or *_base used in glsl is not declared."""
    declared_v = _declared_v_identifiers(glsl)
    declared_base = _declared_base_identifiers(glsl)
    used_v = _used_v_identifiers(glsl)
    used_base = _used_base_identifiers(glsl)

    undeclared_v = used_v - declared_v
    undeclared_base = used_base - declared_base

    if undeclared_v:
        raise AssertionError(
            f"GLSL uses v_* variables that are never declared: {sorted(undeclared_v)}. "
            f"Declared: {sorted(declared_v)}."
        )
    if undeclared_base:
        raise AssertionError(
            f"GLSL uses *_base never defined: {sorted(undeclared_base)}. "
            f"Defined: {sorted(declared_base)}."
        )


def _time_input_ids() -> set[str]:
    """Time network input ids that get _base in the dual shader."""
    return {s.id for s in catalog.DUAL_CPPN_TIME_INPUTS if glsl_uniform_name(s)}


def test_dual_shader_all_signal_variables_declared(
    dual_cppn_representation, random_dual_genome
):
    """Dual shader: every v_* and *_base used in the output is declared/defined."""
    glsl = dual_cppn_representation.develop(random_dual_genome)
    assert glsl is not None and "void main()" in glsl
    _assert_all_used_vars_declared(glsl)


def test_dual_shader_no_redefinition(dual_cppn_representation, random_dual_genome):
    """Dual shader must not declare the same v_* twice (WebGL redefinition)."""
    glsl = dual_cppn_representation.develop(random_dual_genome)
    assert glsl is not None
    redefs = _v_redefinitions(glsl)
    assert not redefs, f"GLSL redefines (declare float twice): {sorted(redefs)}"


def test_single_shader_all_signal_variables_declared():
    """Single CPPN shader: every v_* used is declared (no _base in single path)."""
    representation = SingleCPPNRepresentation()
    genome = representation.create_random(key=0)
    glsl = representation.develop(genome)
    assert glsl is not None and "void main()" in glsl
    _assert_all_used_vars_declared(glsl)


def test_dual_shader_base_variables_only_for_time_inputs(
    dual_cppn_representation, random_dual_genome
):
    """Regression: dual shader must not reference *_base for visual-only signals.

    Only time network inputs get _base in the dual shader. Visual-only inputs
    (e.g. mouse_x, mouse_y) must not be referenced as mouse_x_base / mouse_y_base.
    """
    glsl = dual_cppn_representation.develop(random_dual_genome)
    assert glsl is not None

    used_base = _used_base_identifiers(glsl)
    allowed_base_ids = _time_input_ids()
    # Every *_base must be <time_signal_id>_base for some time input
    for name in used_base:
        base_id = name.removesuffix("_base")
        assert base_id in allowed_base_ids, (
            f"Dual shader must not use '{name}'; "
            f"_base is only for time inputs {sorted(allowed_base_ids)}."
        )


def test_glsl_validity_with_minimal_dual(representation, minimal_dual):
    """Minimal dual genome still produces GLSL with all variables declared."""
    glsl = representation.develop(minimal_dual)
    assert glsl is not None
    _assert_all_used_vars_declared(glsl)


def test_glsl_validity_dual_empty_connections(representation, random_dual_genome):
    """Dual with all connections disabled still has valid variable declarations."""
    dual = random_dual_genome
    for conn in dual.visual.connections.values():
        conn.enabled = False
    for conn in dual.time_signal.connections.values():
        conn.enabled = False
    glsl = representation.develop(dual)
    assert glsl is not None
    _assert_all_used_vars_declared(glsl)

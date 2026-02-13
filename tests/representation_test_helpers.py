"""Shared test helpers for representation protocol compliance and GLSL validation.

Use assert_representation_protocol_compliance(representation) to verify a
representation implements the full protocol (create_random, mutate, crossover,
express, compile_to_shader, to_json/from_json, signal_spec). Optional GLSL
variable check when compile_to_shader returns a string.
"""

from __future__ import annotations

from eyecatcher.representation import RepresentationOutput
from eyecatcher.signals.spec import SignalSpec

# Import GLSL validation from test_glsl_validity so representations can reuse it
from tests.test_glsl_validity import _assert_all_used_vars_declared


def assert_representation_protocol_compliance(
    representation, *, express_inputs: dict | None = None
) -> None:
    """Assert that a representation implements the protocol correctly.

    Checks: create_random, mutate, crossover, express (returns
    RepresentationOutput), to_json/from_json round-trip,
    compile_to_shader (if not None, contains void main() and passes
    GLSL variable declaration checks), signal_spec (is a SignalSpec).

    Args:
        representation: Any object implementing the Representation protocol.
        express_inputs: Optional inputs dict for express(ind, inputs). Default {}.
    """
    inputs = express_inputs if express_inputs is not None else {}
    ind = representation.create_random(key=0)
    assert ind is not None, "create_random must return a non-None individual"

    mutated = representation.mutate(ind, key=1)
    assert mutated is not None, "mutate must return a non-None individual"

    child = representation.crossover(ind, mutated, key=2)
    assert child is not None, "crossover must return a non-None individual"

    output = representation.express(ind, inputs)
    assert isinstance(
        output, RepresentationOutput
    ), "express must return RepresentationOutput"
    assert output.output_type == representation.output_type

    data = representation.to_json(ind)
    restored = representation.from_json(data)
    restored_data = representation.to_json(restored)
    assert data == restored_data, "to_json/from_json round-trip must preserve data"

    glsl = representation.compile_to_shader(ind)
    if glsl is not None:
        assert (
            "void main()" in glsl
        ), "compile_to_shader output must contain void main()"
        _assert_all_used_vars_declared(glsl)

    # signal_spec must be present and well-formed
    spec = getattr(representation, "signal_spec", None)
    assert spec is not None, "representation must have a signal_spec"
    assert isinstance(spec, SignalSpec), "signal_spec must be a SignalSpec"

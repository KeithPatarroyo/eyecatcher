"""Shared test helpers for substrate protocol compliance and GLSL validation.

Use assert_substrate_protocol_compliance(substrate) to verify a substrate
implements the full protocol (create_random, mutate, crossover, evaluate,
compile_to_shader, to_json/from_json). Optional GLSL variable check when
compile_to_shader returns a string.
"""

from __future__ import annotations

from eyecatcher.substrate import SubstrateOutput

# Import GLSL validation from test_glsl_validity so substrates can reuse it
from tests.test_glsl_validity import _assert_all_used_vars_declared


def assert_substrate_protocol_compliance(
    substrate, *, evaluate_inputs: dict | None = None
) -> None:
    """Assert that a substrate implements the protocol correctly.

    Checks: create_random, mutate, crossover, evaluate (returns SubstrateOutput),
    to_json/from_json round-trip, compile_to_shader (if not None, contains void main()
    and passes GLSL variable declaration checks).

    Args:
        substrate: Any object implementing the Substrate protocol.
        evaluate_inputs: Optional inputs dict for evaluate(ind, inputs). Default {}.
    """
    inputs = evaluate_inputs if evaluate_inputs is not None else {}
    ind = substrate.create_random(key=0)
    assert ind is not None, "create_random must return a non-None individual"

    mutated = substrate.mutate(ind, key=1)
    assert mutated is not None, "mutate must return a non-None individual"

    child = substrate.crossover(ind, mutated, key=2)
    assert child is not None, "crossover must return a non-None individual"

    output = substrate.evaluate(ind, inputs)
    assert isinstance(output, SubstrateOutput), "evaluate must return SubstrateOutput"
    assert output.output_type == substrate.output_type

    data = substrate.to_json(ind)
    restored = substrate.from_json(data)
    restored_data = substrate.to_json(restored)
    assert data == restored_data, "to_json/from_json round-trip must preserve data"

    glsl = substrate.compile_to_shader(ind)
    if glsl is not None:
        assert (
            "void main()" in glsl
        ), "compile_to_shader output must contain void main()"
        _assert_all_used_vars_declared(glsl)

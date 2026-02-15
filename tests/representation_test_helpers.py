"""Shared test helpers for representation protocol compliance and GLSL validation.

Use assert_representation_protocol_compliance(representation) to verify a
representation implements the full protocol (create_random, mutate, crossover,
express, develop, to_json/from_json, sensory_system). Optional GLSL variable
check when develop returns a string.
"""

from __future__ import annotations

from eyecatcher.representation import RepresentationOutput
from eyecatcher.signals.sensory_system import SensorySystem

# Import GLSL validation from test_glsl_validity so representations can reuse it
from tests.test_glsl_validity import _assert_all_used_vars_declared


def assert_representation_protocol_compliance(
    representation, *, express_inputs: dict | None = None
) -> None:
    """Assert that a representation implements the protocol correctly.

    Checks: create_random, mutate, crossover, express (returns
    RepresentationOutput), to_json/from_json round-trip, develop (if not None,
    contains void main() and passes GLSL variable declaration checks),
    sensory_system (is a SensorySystem).

    Args:
        representation: Any object implementing the Representation protocol.
        express_inputs: Optional inputs dict for express(genome, inputs). Default {}.
    """
    inputs = express_inputs if express_inputs is not None else {}
    genome = representation.create_random(key=0)
    assert genome is not None, "create_random must return a non-None genome"

    mutated = representation.mutate(genome, key=1)
    assert mutated is not None, "mutate must return a non-None genome"

    child = representation.crossover(genome, mutated, key=2)
    assert child is not None, "crossover must return a non-None genome"

    output = representation.express(genome, inputs)
    assert isinstance(
        output, RepresentationOutput
    ), "express must return RepresentationOutput"
    assert output.output_type == representation.output_type

    data = representation.to_json(genome)
    restored = representation.from_json(data)
    restored_data = representation.to_json(restored)
    assert data == restored_data, "to_json/from_json round-trip must preserve data"

    glsl = representation.develop(genome)
    if glsl is not None:
        assert "void main()" in glsl, "develop output must contain void main()"
        _assert_all_used_vars_declared(glsl)

    # sensory_system must be present and well-formed
    env = getattr(representation, "sensory_system", None)
    assert env is not None, "representation must have a sensory_system"
    assert isinstance(env, SensorySystem), "sensory_system must be a SensorySystem"

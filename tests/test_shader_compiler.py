"""Tests for rule assembler: CPPN develop to GLSL via receptors."""

from eyecatcher.glsl import RuleAssembler
from eyecatcher.glsl.activation_registry import get_activation_names_sorted

from tests.conftest import minimal_dual_genome_one_hidden_visual


def test_compile_dual_to_glsl_returns_string(representation, random_dual_genome):
    """develop returns a non-empty GLSL string for dual genome."""
    glsl = representation.develop(random_dual_genome)
    assert isinstance(glsl, str)
    assert len(glsl) > 0


def test_compile_dual_to_glsl_contains_main(representation, random_dual_genome):
    """Output GLSL contains void main()."""
    glsl = representation.develop(random_dual_genome)
    assert "void main()" in glsl


def test_compile_dual_to_glsl_rgb_mode(representation, random_dual_genome):
    """develop works with color_mode='rgb'."""
    glsl = representation.develop(random_dual_genome, color_mode="rgb")
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_empty_connections(representation, random_dual_genome):
    """develop handles genome with no enabled connections (minimal output)."""
    dual = random_dual_genome
    for conn in dual.visual.connections.values():
        conn.enabled = False
    for conn in dual.time_signal.connections.values():
        conn.enabled = False
    glsl = representation.develop(dual)
    assert isinstance(glsl, str)
    assert "void main()" in glsl


def test_compile_dual_single_hidden_node(representation):
    """develop with exactly one hidden node in visual CPPN (deterministic)."""
    dual = minimal_dual_genome_one_hidden_visual(representation)
    num_out = representation.config.genome_config.num_outputs
    hidden_visual = [n for n in dual.visual.nodes if n >= num_out]
    assert (
        len(hidden_visual) == 1
    ), "test fixture must have exactly one hidden node in visual"
    glsl = representation.develop(dual)
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_activation_functions_in_output(
    representation, random_dual_genome
):
    """Compiled GLSL contains at least one known activation function call."""
    glsl = representation.develop(random_dual_genome)
    activations_found = [
        name for name in get_activation_names_sorted() if f"{name}(" in glsl
    ]
    assert len(activations_found) >= 1, "expected at least one activation in output"


def test_rule_assembler_importable():
    """RuleAssembler is the public API for assembling rules."""
    assert RuleAssembler is not None
    assert hasattr(RuleAssembler, "from_sensory_system")
    assert hasattr(RuleAssembler, "assemble")

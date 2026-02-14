"""Tests for shader compiler: CPPN to GLSL."""

from eyecatcher.glsl import ShaderCompiler
from eyecatcher.glsl.activation_registry import get_activation_names_sorted

from tests.conftest import minimal_dual_genome_one_hidden_visual


def _compiler_from_rep(representation, color_mode="hsv"):
    """Build a ShaderCompiler from a representation's signal_spec."""
    return ShaderCompiler.from_spec(representation.signal_spec, color_mode=color_mode)


def test_compile_dual_to_glsl_returns_string(representation, random_dual_genome):
    """compile returns a non-empty GLSL string for dual genome."""
    compiler = _compiler_from_rep(representation)
    glsl = compiler.compile(
        random_dual_genome.visual,
        representation.config,
        random_dual_genome.time_signal,
        representation.time_config,
    )
    assert isinstance(glsl, str)
    assert len(glsl) > 0


def test_compile_dual_to_glsl_contains_main(representation, random_dual_genome):
    """Output GLSL contains void main()."""
    compiler = _compiler_from_rep(representation)
    glsl = compiler.compile(
        random_dual_genome.visual,
        representation.config,
        random_dual_genome.time_signal,
        representation.time_config,
    )
    assert "void main()" in glsl


def test_compile_dual_to_glsl_rgb_mode(representation, random_dual_genome):
    """Compiler works with color_mode='rgb'."""
    compiler = _compiler_from_rep(representation, color_mode="rgb")
    glsl = compiler.compile(
        random_dual_genome.visual,
        representation.config,
        random_dual_genome.time_signal,
        representation.time_config,
    )
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_empty_connections(representation, random_dual_genome):
    """Compiler handles genome with no enabled connections (minimal output)."""
    dual = random_dual_genome
    for conn in dual.visual.connections.values():
        conn.enabled = False
    for conn in dual.time_signal.connections.values():
        conn.enabled = False
    compiler = _compiler_from_rep(representation)
    glsl = compiler.compile(
        dual.visual, representation.config, dual.time_signal, representation.time_config
    )
    assert isinstance(glsl, str)
    assert "void main()" in glsl


def test_compile_dual_single_hidden_node(representation):
    """Compiler with exactly one hidden node in visual CPPN (deterministic)."""
    dual = minimal_dual_genome_one_hidden_visual(representation)
    num_out = representation.config.genome_config.num_outputs
    hidden_visual = [n for n in dual.visual.nodes if n >= num_out]
    assert (
        len(hidden_visual) == 1
    ), "test fixture must have exactly one hidden node in visual"
    compiler = _compiler_from_rep(representation)
    glsl = compiler.compile(
        dual.visual, representation.config, dual.time_signal, representation.time_config
    )
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_activation_functions_in_output(
    representation, random_dual_genome
):
    """Compiled GLSL contains at least one known activation function call."""
    compiler = _compiler_from_rep(representation)
    glsl = compiler.compile(
        random_dual_genome.visual,
        representation.config,
        random_dual_genome.time_signal,
        representation.time_config,
    )
    activations_found = [
        name for name in get_activation_names_sorted() if f"{name}(" in glsl
    ]
    assert len(activations_found) >= 1, "expected at least one activation in output"

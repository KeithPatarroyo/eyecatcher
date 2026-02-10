"""Tests for shader compiler: CPPN to GLSL."""

from conftest import minimal_dual_genome_one_hidden_visual
from eyecatcher.evolution.shader_compiler import ShaderCompiler


def test_compile_dual_to_glsl_returns_string(cppn_engine, random_dual_genome):
    """compile_dual_to_glsl returns a non-empty GLSL string."""
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(
        random_dual_genome, cppn_engine.config, cppn_engine.time_config
    )
    assert isinstance(glsl, str)
    assert len(glsl) > 0


def test_compile_dual_to_glsl_contains_main(cppn_engine, random_dual_genome):
    """Output GLSL contains void main()."""
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(
        random_dual_genome, cppn_engine.config, cppn_engine.time_config
    )
    assert "void main()" in glsl


def test_compile_dual_to_glsl_rgb_mode(cppn_engine, random_dual_genome):
    """Compiler works with color_mode='rgb'."""
    compiler = ShaderCompiler(color_mode="rgb")
    glsl = compiler.compile_dual_to_glsl(
        random_dual_genome, cppn_engine.config, cppn_engine.time_config
    )
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_empty_connections(cppn_engine, random_dual_genome):
    """Compiler handles genome with no enabled connections (minimal output)."""
    dual = random_dual_genome
    for conn in dual.visual.connections.values():
        conn.enabled = False
    for conn in dual.time_signal.connections.values():
        conn.enabled = False
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(
        dual, cppn_engine.config, cppn_engine.time_config
    )
    assert isinstance(glsl, str)
    assert "void main()" in glsl


def test_compile_dual_single_hidden_node(cppn_engine):
    """Compiler with exactly one hidden node in visual CPPN (deterministic)."""
    dual = minimal_dual_genome_one_hidden_visual(cppn_engine)
    hidden_visual = [
        n
        for n in dual.visual.nodes
        if n >= cppn_engine.config.genome_config.num_outputs
    ]
    assert (
        len(hidden_visual) == 1
    ), "test fixture must have exactly one hidden node in visual"
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(
        dual, cppn_engine.config, cppn_engine.time_config
    )
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_activation_functions_in_output(cppn_engine, random_dual_genome):
    """Compiled GLSL contains at least one known activation function call."""
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(
        random_dual_genome, cppn_engine.config, cppn_engine.time_config
    )
    activations_found = [
        name for name in ShaderCompiler.ACTIVATION_FUNCTIONS if f"{name}(" in glsl
    ]
    assert len(activations_found) >= 1, "expected at least one activation in output"

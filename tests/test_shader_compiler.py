"""Tests for shader compiler: CPPN to GLSL."""

from eyecatcher.cppn_engine import CPPNEngine, create_random_dual_genome
from eyecatcher.shader_compiler import ShaderCompiler


def test_compile_dual_to_glsl_returns_string():
    """compile_dual_to_glsl returns a non-empty GLSL string."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    assert isinstance(glsl, str)
    assert len(glsl) > 0


def test_compile_dual_to_glsl_contains_main():
    """Output GLSL contains void main()."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    assert "void main()" in glsl


def test_compile_dual_to_glsl_rgb_mode():
    """Compiler works with color_mode='rgb'."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    compiler = ShaderCompiler(color_mode="rgb")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    assert "void main()" in glsl
    assert len(glsl) > 0

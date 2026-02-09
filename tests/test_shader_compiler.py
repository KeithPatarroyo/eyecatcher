"""Tests for shader compiler: CPPN to GLSL."""

from eyecatcher.cppn_engine import CPPNEngine, create_random_dual_genome
from eyecatcher.genome_serialization import dual_genome_from_json
from eyecatcher.shader_compiler import ShaderCompiler


def _minimal_dual_genome_one_hidden_visual(engine: CPPNEngine):
    """Dual genome with exactly one hidden node in the visual CPPN (deterministic)."""
    vc = engine.config.genome_config
    tc = engine.time_config.genome_config
    # Visual: 8 inputs (-8..-1), 3 outputs (0,1,2), one hidden (3). Path: -1 -> 3 -> 0.
    visual_nodes = {
        str(i): {
            "bias": 0.0,
            "response": 1.0,
            "activation": "sigmoid",
            "aggregation": "sum",
        }
        for i in list(range(-vc.num_inputs, 0))
        + list(range(vc.num_outputs))
        + [vc.num_outputs]
    }
    visual_conns = {
        "-1_3": {"innovation": 1, "weight": 0.5, "enabled": True},
        "3_0": {"innovation": 2, "weight": 0.5, "enabled": True},
    }
    # Time: 5 inputs, 1 output. One connection -1 -> 0.
    time_nodes = {
        str(i): {
            "bias": 0.0,
            "response": 1.0,
            "activation": "sigmoid",
            "aggregation": "sum",
        }
        for i in list(range(-tc.num_inputs, 0)) + [0]
    }
    time_conns = {"-1_0": {"innovation": 1, "weight": 0.5, "enabled": True}}
    data = {
        "key": 0,
        "visual": {
            "key": 0,
            "fitness": None,
            "nodes": visual_nodes,
            "connections": visual_conns,
        },
        "time_signal": {
            "key": 0,
            "fitness": None,
            "nodes": time_nodes,
            "connections": time_conns,
        },
    }
    return dual_genome_from_json(data, engine)


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


def test_compile_dual_empty_connections():
    """Compiler handles genome with no enabled connections (minimal output)."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    for conn in dual.visual.connections.values():
        conn.enabled = False
    for conn in dual.time_signal.connections.values():
        conn.enabled = False
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    assert isinstance(glsl, str)
    assert "void main()" in glsl


def test_compile_dual_single_hidden_node():
    """Compiler with exactly one hidden node in visual CPPN (deterministic)."""
    engine = CPPNEngine()
    engine.create_population()
    dual = _minimal_dual_genome_one_hidden_visual(engine)
    hidden_visual = [
        n for n in dual.visual.nodes if n >= engine.config.genome_config.num_outputs
    ]
    assert (
        len(hidden_visual) == 1
    ), "test fixture must have exactly one hidden node in visual"
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    assert "void main()" in glsl
    assert len(glsl) > 0


def test_compile_dual_activation_functions_in_output():
    """Compiled GLSL contains at least one known activation function call."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    compiler = ShaderCompiler(color_mode="hsv")
    glsl = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    # GLSL calls look like "sigmoid(", "tanh(", etc.
    activations_found = [
        name for name in ShaderCompiler.ACTIVATION_FUNCTIONS if f"{name}(" in glsl
    ]
    assert len(activations_found) >= 1, "expected at least one activation in output"

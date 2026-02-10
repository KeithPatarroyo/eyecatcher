"""Tests for response_builder.build_shader_response."""

from eyecatcher.evolution import dual_genome_network_stats
from eyecatcher.evolution.shader_compiler import ShaderCompiler
from eyecatcher.response_builder import build_shader_response


def test_build_shader_response_returns_expected_keys(cppn_engine, random_dual_genome):
    """Returns id, shader, clicks, nodes, connections, visual_*, time_*."""
    compiler = ShaderCompiler(color_mode="hsv")
    resp = build_shader_response(
        random_dual_genome,
        individual_id=42,
        clicks=3,
        compiler=compiler,
        visual_config=cppn_engine.config,
        time_config=cppn_engine.time_config,
    )
    expected = {
        "id",
        "shader",
        "clicks",
        "nodes",
        "connections",
        "visual_nodes",
        "visual_connections",
        "time_nodes",
        "time_connections",
    }
    assert expected <= set(resp.keys())
    assert resp["id"] == 42
    assert resp["clicks"] == 3
    assert "void main()" in resp["shader"]


def test_build_shader_response_stats_match_dual_genome_network_stats(
    cppn_engine, random_dual_genome
):
    """Counts match dual_genome_network_stats; nodes/connections are sums."""
    compiler = ShaderCompiler(color_mode="hsv")
    resp = build_shader_response(
        random_dual_genome,
        individual_id=0,
        clicks=0,
        compiler=compiler,
        visual_config=cppn_engine.config,
        time_config=cppn_engine.time_config,
    )
    stats = dual_genome_network_stats(random_dual_genome)
    assert resp["visual_nodes"] == stats["visual_nodes"]
    assert resp["visual_connections"] == stats["visual_connections"]
    assert resp["time_nodes"] == stats["time_nodes"]
    assert resp["time_connections"] == stats["time_connections"]
    assert resp["nodes"] == stats["visual_nodes"] + stats["time_nodes"]
    assert (
        resp["connections"] == stats["visual_connections"] + stats["time_connections"]
    )


def test_build_shader_response_extra_metadata_merged(cppn_engine, random_dual_genome):
    """extra_metadata keys are merged into the returned dict."""
    compiler = ShaderCompiler(color_mode="hsv")
    resp = build_shader_response(
        random_dual_genome,
        individual_id=0,
        clicks=0,
        compiler=compiler,
        visual_config=cppn_engine.config,
        time_config=cppn_engine.time_config,
        extra_metadata={"compile_version": 1, "custom": "value"},
    )
    assert resp["compile_version"] == 1
    assert resp["custom"] == "value"

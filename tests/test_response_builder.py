"""Tests for substrate compile stats (formerly response_builder)."""

from eyecatcher.evaluation import dual_genome_network_stats


def test_get_compile_stats_returns_expected_keys(
    dual_cppn_substrate, random_dual_genome
):
    """get_compile_stats returns visual/time node and connection counts."""
    stats = dual_cppn_substrate.get_compile_stats(random_dual_genome)
    assert stats is not None
    expected = {
        "visual_nodes",
        "visual_connections",
        "time_nodes",
        "time_connections",
    }
    assert expected <= set(stats.keys())


def test_get_compile_stats_matches_dual_genome_network_stats(
    dual_cppn_substrate, random_dual_genome
):
    """Compile stats match dual_genome_network_stats directly."""
    stats = dual_cppn_substrate.get_compile_stats(random_dual_genome)
    direct = dual_genome_network_stats(random_dual_genome)
    assert stats["visual_nodes"] == direct["visual_nodes"]
    assert stats["visual_connections"] == direct["visual_connections"]
    assert stats["time_nodes"] == direct["time_nodes"]
    assert stats["time_connections"] == direct["time_connections"]


def test_compile_to_shader_returns_valid_glsl(dual_cppn_substrate, random_dual_genome):
    """compile_to_shader returns GLSL with void main()."""
    shader = dual_cppn_substrate.compile_to_shader(random_dual_genome)
    assert shader is not None
    assert "void main()" in shader

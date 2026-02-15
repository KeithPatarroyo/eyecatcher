"""Tests for representation develop stats and develop (genome → shader)."""


def test_get_develop_stats_returns_expected_keys(
    dual_cppn_representation, random_dual_genome
):
    """get_develop_stats returns visual/time node and connection counts."""
    stats = dual_cppn_representation.get_develop_stats(random_dual_genome)
    assert stats is not None
    expected = {
        "visual_nodes",
        "visual_connections",
        "time_nodes",
        "time_connections",
    }
    assert expected <= set(stats.keys())


def test_get_develop_stats_matches_genome_structure(
    dual_cppn_representation, random_dual_genome
):
    """Develop stats reflect actual node/connection counts from the genome."""
    stats = dual_cppn_representation.get_develop_stats(random_dual_genome)
    ind = random_dual_genome
    assert stats["visual_nodes"] == len(ind.visual.nodes)
    assert stats["visual_connections"] == len(
        [c for c in ind.visual.connections.values() if c.enabled]
    )
    assert stats["time_nodes"] == len(ind.time_signal.nodes)
    assert stats["time_connections"] == len(
        [c for c in ind.time_signal.connections.values() if c.enabled]
    )


def test_develop_returns_valid_glsl(dual_cppn_representation, random_dual_genome):
    """develop returns GLSL with void main()."""
    shader = dual_cppn_representation.develop(random_dual_genome)
    assert shader is not None
    assert "void main()" in shader

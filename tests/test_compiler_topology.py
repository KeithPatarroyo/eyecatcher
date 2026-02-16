"""Tests for compiler topology: enabled connections and evaluation order."""

from eyecatcher.representation.receptors import (
    _get_enabled_connections as get_enabled_connections,
)
from eyecatcher.representation.receptors import (
    _topological_sort as topological_sort,
)


def test_get_enabled_connections_returns_only_enabled(
    representation, random_dual_genome
):
    """get_enabled_connections returns (src, dst, weight) for enabled only."""
    genome = random_dual_genome.visual
    keys = list(genome.connections.keys())[:3]
    for k in genome.connections:
        genome.connections[k].enabled = k in keys

    conns = get_enabled_connections(genome)
    assert len(conns) == len(keys)
    for src, dst, w in conns:
        assert (src, dst) in keys
        assert isinstance(w, int | float)


def test_get_enabled_connections_empty_when_all_disabled(random_dual_genome):
    """get_enabled_connections returns empty list when all connections disabled."""
    genome = random_dual_genome.visual
    for c in genome.connections.values():
        c.enabled = False
    assert get_enabled_connections(genome) == []


def test_topological_sort_respects_input_output_indices(
    representation, random_dual_genome
):
    """topological_sort returns order where inputs/outputs use config indices."""
    genome = random_dual_genome.visual
    config = representation.config
    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    connections = get_enabled_connections(genome)
    nodes = topological_sort(genome, connections, config)

    input_nodes = list(range(-num_inputs, 0))
    output_nodes = list(range(num_outputs))
    for n in input_nodes:
        assert n in nodes
    for n in output_nodes:
        assert n in nodes
    assert len(nodes) >= len(input_nodes) + len(output_nodes)


def test_topological_sort_deterministic(representation, random_dual_genome):
    """topological_sort is deterministic for same genome."""
    genome = random_dual_genome.visual
    config = representation.config
    connections = get_enabled_connections(genome)
    a = topological_sort(genome, connections, config)
    b = topological_sort(genome, connections, config)
    assert a == b

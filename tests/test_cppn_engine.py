"""Tests for dual-CPPN representation: population, mutation, crossover, query."""

from eyecatcher.evolution import mutate_genome
from eyecatcher.genome import create_random_genome
from eyecatcher.representation import DualGenome


def test_engine_create_population(representation):
    """Substrate has configs and population."""
    assert representation.config is not None
    assert representation.time_config is not None
    assert representation.population is not None
    assert representation.time_population is not None


def test_create_random_dual_genome(representation):
    """create_random returns a DualGenome with visual and time_signal."""
    dual = representation.create_random(key=3)
    assert isinstance(dual, DualGenome)
    assert dual.visual is not None
    assert dual.time_signal is not None
    assert dual.key == 3


def test_query_dual_cppn_returns_rgb(representation, random_dual_genome):
    """Substrate._query_dual_cppn returns (r, g, b) in 0-1."""
    inputs = {"x": 0.0, "y": 0.0, "raw_time": 0.0}
    r, g, b = representation.query_rgb(random_dual_genome, inputs)
    assert 0 <= r <= 1
    assert 0 <= g <= 1
    assert 0 <= b <= 1


def test_mutate_dual_genome(representation, random_dual_genome):
    """representation.mutate returns a new DualGenome."""
    mutated = representation.mutate(random_dual_genome, 1)
    assert isinstance(mutated, DualGenome)
    assert mutated.key == 1
    assert (
        mutated.visual is not random_dual_genome.visual
        or mutated.time_signal is not random_dual_genome.time_signal
    )


def test_crossover_dual_genomes(representation):
    """representation.crossover returns a child DualGenome."""
    a = representation.create_random(key=0)
    b = representation.create_random(key=1)
    child = representation.crossover(a, b, 2)
    assert isinstance(child, DualGenome)
    assert child.key == 2
    assert child.visual is not None
    assert child.time_signal is not None


def test_create_random_genome_and_mutate(representation):
    """Single-genome path: create_random_genome and mutate_genome work."""
    genome = create_random_genome(representation.config, genome_id=42)
    assert genome is not None
    mutated = mutate_genome(genome, representation.config)
    assert mutated is not None
    assert mutated.key == 43, "mutate returns child with parent_key + 1"
    assert isinstance(mutated.nodes, dict)
    assert isinstance(mutated.connections, dict)
    assert len(mutated.nodes) >= representation.config.genome_config.num_outputs

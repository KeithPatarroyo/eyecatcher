"""Tests for dual-CPPN substrate: population, mutation, crossover, query."""

from eyecatcher.evolution import mutate_genome
from eyecatcher.genome import create_random_genome
from eyecatcher.substrate import DualGenome


def test_engine_create_population(substrate):
    """Substrate has configs and population."""
    assert substrate.config is not None
    assert substrate.time_config is not None
    assert substrate.population is not None
    assert substrate.time_population is not None


def test_create_random_dual_genome(substrate):
    """create_random returns a DualGenome with visual and time_signal."""
    dual = substrate.create_random(key=3)
    assert isinstance(dual, DualGenome)
    assert dual.visual is not None
    assert dual.time_signal is not None
    assert dual.key == 3


def test_query_dual_cppn_returns_rgb(substrate, random_dual_genome):
    """Substrate._query_dual_cppn returns (r, g, b) in 0-1."""
    inputs = {"x": 0.0, "y": 0.0, "raw_time": 0.0}
    r, g, b = substrate.query_rgb(random_dual_genome, inputs)
    assert 0 <= r <= 1
    assert 0 <= g <= 1
    assert 0 <= b <= 1


def test_mutate_dual_genome(substrate, random_dual_genome):
    """substrate.mutate returns a new DualGenome."""
    mutated = substrate.mutate(random_dual_genome, 1)
    assert isinstance(mutated, DualGenome)
    assert mutated.key == 1
    assert (
        mutated.visual is not random_dual_genome.visual
        or mutated.time_signal is not random_dual_genome.time_signal
    )


def test_crossover_dual_genomes(substrate):
    """substrate.crossover returns a child DualGenome."""
    a = substrate.create_random(key=0)
    b = substrate.create_random(key=1)
    child = substrate.crossover(a, b, 2)
    assert isinstance(child, DualGenome)
    assert child.key == 2
    assert child.visual is not None
    assert child.time_signal is not None


def test_create_random_genome_and_mutate(substrate):
    """Single-genome path: create_random_genome and mutate_genome work."""
    genome = create_random_genome(substrate.config, genome_id=42)
    assert genome is not None
    mutated = mutate_genome(genome, substrate.config)
    assert mutated is not None
    assert mutated.key == 43, "mutate returns child with parent_key + 1"
    assert isinstance(mutated.nodes, dict)
    assert isinstance(mutated.connections, dict)
    assert len(mutated.nodes) >= substrate.config.genome_config.num_outputs

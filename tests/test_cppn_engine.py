"""Tests for CPPN engine: population, mutation, crossover, query."""

from eyecatcher.evolution import (
    DualGenome,
    create_random_dual_genome,
    create_random_genome,
)
from eyecatcher.evolution.operators import mutate_single_genome


def test_engine_create_population(cppn_engine):
    """Engine creates population and has configs."""
    assert cppn_engine.config is not None
    assert cppn_engine.time_config is not None
    assert cppn_engine.population is not None
    assert cppn_engine.time_population is not None


def test_create_random_dual_genome(cppn_engine):
    """create_random_dual_genome returns a DualGenome with visual and time_signal."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=3
    )
    assert isinstance(dual, DualGenome)
    assert dual.visual is not None
    assert dual.time_signal is not None
    assert dual.key == 3


def test_query_dual_cppn_returns_rgb(cppn_engine, random_dual_genome):
    """query_dual_cppn returns three values in 0-255."""
    inputs = {"x": 0.0, "y": 0.0, "raw_time": 0.0}
    r, g, b = cppn_engine.query_dual_cppn(random_dual_genome, inputs)
    assert 0 <= r <= 255
    assert 0 <= g <= 255
    assert 0 <= b <= 255


def test_mutate_dual_genome(cppn_engine, random_dual_genome):
    """mutate_dual_genome returns a new DualGenome."""
    mutated = cppn_engine.mutate_dual_genome(random_dual_genome, new_key=1)
    assert isinstance(mutated, DualGenome)
    assert mutated.key == 1
    assert (
        mutated.visual is not random_dual_genome.visual
        or mutated.time_signal is not random_dual_genome.time_signal
    )


def test_crossover_dual_genomes(cppn_engine):
    """crossover_dual_genomes returns a child DualGenome."""
    a = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )
    b = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=1
    )
    child = cppn_engine.crossover_dual_genomes(a, b, new_key=2)
    assert isinstance(child, DualGenome)
    assert child.key == 2
    assert child.visual is not None
    assert child.time_signal is not None


def test_create_random_genome_and_mutate(cppn_engine):
    """Single-genome path: create_random_genome and mutate_single_genome work."""
    genome = create_random_genome(cppn_engine.config, genome_id=42)
    assert genome is not None
    mutated = mutate_single_genome(genome, cppn_engine.config)
    assert mutated is not None
    assert mutated.key == 43, "mutate returns child with parent_key + 1"
    assert isinstance(mutated.nodes, dict)
    assert isinstance(mutated.connections, dict)
    assert len(mutated.nodes) >= cppn_engine.config.genome_config.num_outputs

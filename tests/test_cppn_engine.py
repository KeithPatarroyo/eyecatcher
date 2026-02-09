"""Tests for CPPN engine: population, mutation, crossover, query."""

from eyecatcher.cppn_engine import (
    CPPNEngine,
    DualGenome,
    create_random_dual_genome,
    create_random_genome,
)


def test_engine_create_population():
    """Engine creates population and has configs."""
    engine = CPPNEngine()
    engine.create_population()
    assert engine.config is not None
    assert engine.time_config is not None
    assert engine.population is not None
    assert engine.time_population is not None


def test_create_random_dual_genome():
    """create_random_dual_genome returns a DualGenome with visual and time_signal."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=3)
    assert isinstance(dual, DualGenome)
    assert dual.visual is not None
    assert dual.time_signal is not None
    assert dual.key == 3


def test_query_dual_cppn_returns_rgb():
    """query_dual_cppn returns three values in 0-255."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    r, g, b = engine.query_dual_cppn(dual, 0.0, 0.0, raw_time=0.0)
    assert 0 <= r <= 255
    assert 0 <= g <= 255
    assert 0 <= b <= 255


def test_mutate_dual_genome():
    """mutate_dual_genome returns a new DualGenome."""
    engine = CPPNEngine()
    engine.create_population()
    dual = create_random_dual_genome(engine, genome_id=0)
    mutated = engine.mutate_dual_genome(dual, new_key=1)
    assert isinstance(mutated, DualGenome)
    assert mutated.key == 1
    assert (
        mutated.visual is not dual.visual or mutated.time_signal is not dual.time_signal
    )


def test_crossover_dual_genomes():
    """crossover_dual_genomes returns a child DualGenome."""
    engine = CPPNEngine()
    engine.create_population()
    a = create_random_dual_genome(engine, genome_id=0)
    b = create_random_dual_genome(engine, genome_id=1)
    child = engine.crossover_dual_genomes(a, b, new_key=2)
    assert isinstance(child, DualGenome)
    assert child.key == 2
    assert child.visual is not None
    assert child.time_signal is not None


def test_create_random_genome_and_mutate():
    """Single-genome path: create_random_genome and mutate_genome work."""
    engine = CPPNEngine()
    engine.create_population()
    genome = create_random_genome(engine.config, genome_id=42)
    assert genome is not None
    mutated = engine.mutate_genome(genome)
    assert mutated is not None
    assert len(mutated.nodes) >= 0
    assert len(mutated.connections) >= 0

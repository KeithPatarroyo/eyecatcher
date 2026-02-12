"""
Mutation and crossover for single and dual genomes.

Used by reproduction and substrates.
"""

import neat

from ..genome.genome import DualGenome
from ..genome.serialization import _update_node_indexer_from_genome


def mutate_single_genome(
    genome: neat.DefaultGenome, visual_config: neat.Config
) -> neat.DefaultGenome:
    """Create a mutated copy of a single genome."""
    _update_node_indexer_from_genome(genome, visual_config.genome_config)
    if genome.fitness is None:
        genome.fitness = 0.0  # type: ignore[assignment]
    parent_key = genome.key if genome.key is not None else 0
    child = neat.DefaultGenome(parent_key + 1)
    child.configure_crossover(genome, genome, visual_config.genome_config)
    child.mutate(visual_config.genome_config)
    child.fitness = None
    return child


def crossover_single_genomes(
    genome1: neat.DefaultGenome,
    genome2: neat.DefaultGenome,
    visual_config: neat.Config,
) -> neat.DefaultGenome:
    """Create offspring from two single genomes."""
    if genome1.fitness is None:
        genome1.fitness = 0.0  # type: ignore[assignment]
    if genome2.fitness is None:
        genome2.fitness = 0.0  # type: ignore[assignment]
    key1 = genome1.key if genome1.key is not None else 0
    key2 = genome2.key if genome2.key is not None else 0
    child = neat.DefaultGenome(max(key1, key2) + 1)
    child.configure_crossover(genome1, genome2, visual_config.genome_config)
    child.fitness = None
    return child


def mutate_dual_genome(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: int,
) -> DualGenome:
    """Create a mutated copy of a dual genome (both visual and time signal)."""
    visual_child = mutate_single_genome(dual_genome.visual, visual_config)
    time_child = mutate_single_genome(dual_genome.time_signal, time_config)
    return DualGenome(visual=visual_child, time_signal=time_child, key=new_key)


def crossover_dual_genomes(
    dual1: DualGenome,
    dual2: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: int,
) -> DualGenome:
    """Create offspring from two dual genomes."""
    visual_child = crossover_single_genomes(dual1.visual, dual2.visual, visual_config)
    time_child = crossover_single_genomes(
        dual1.time_signal, dual2.time_signal, time_config
    )
    return DualGenome(visual=visual_child, time_signal=time_child, key=new_key)

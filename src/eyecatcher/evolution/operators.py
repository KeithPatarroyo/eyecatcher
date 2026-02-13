"""
Mutation and crossover for NEAT genomes.

Used by reproduction and CPPN substrates. Dual-genome operators live in
substrate.dual_genome (used by DualCPPNSubstrate only).
"""

import neat

from ..genome.serialization import _update_node_indexer_from_genome


def mutate_genome(
    genome: neat.DefaultGenome, neat_config: neat.Config
) -> neat.DefaultGenome:
    """Create a mutated copy of a genome."""
    _update_node_indexer_from_genome(genome, neat_config.genome_config)
    if genome.fitness is None:
        genome.fitness = 0.0  # type: ignore[assignment]
    parent_key = genome.key if genome.key is not None else 0
    child = neat.DefaultGenome(parent_key + 1)
    child.configure_crossover(genome, genome, neat_config.genome_config)
    child.mutate(neat_config.genome_config)
    child.fitness = None
    return child


def crossover_genomes(
    genome1: neat.DefaultGenome,
    genome2: neat.DefaultGenome,
    neat_config: neat.Config,
) -> neat.DefaultGenome:
    """Create offspring from two genomes."""
    if genome1.fitness is None:
        genome1.fitness = 0.0  # type: ignore[assignment]
    if genome2.fitness is None:
        genome2.fitness = 0.0  # type: ignore[assignment]
    key1 = genome1.key if genome1.key is not None else 0
    key2 = genome2.key if genome2.key is not None else 0
    child = neat.DefaultGenome(max(key1, key2) + 1)
    child.configure_crossover(genome1, genome2, neat_config.genome_config)
    child.fitness = None
    return child

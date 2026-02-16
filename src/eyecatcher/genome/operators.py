"""
Genome operations: create, mutate, crossover, and custom activation registration.

Used by reproduction and CPPN substrates. Dual-genome operators live in
genome.dual (used by DualCPPNSubstrate only). register_custom_activations is
called from substrate init (dual_cppn, single_cppn).
"""

import math

import neat

from .serialization import _update_node_indexer_from_genome


def _cos_activation(x: float) -> float:
    """Cosine activation function."""
    return math.cos(x)


def register_custom_activations(config: neat.Config) -> None:
    """Register custom activation functions with a NEAT config."""
    activation_defs = config.genome_config.activation_defs
    if "cos" not in activation_defs.functions:
        activation_defs.add("cos", _cos_activation)


def create_random_genome(
    neat_config: neat.Config, genome_id: int = 0
) -> neat.DefaultGenome:
    """
    Create a random genome with the given configuration.

    Args:
        neat_config: NEAT configuration for the genome
        genome_id: ID for the genome

    Returns:
        Randomly initialized genome
    """
    genome = neat.DefaultGenome(genome_id)
    genome.configure_new(neat_config.genome_config)
    return genome


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

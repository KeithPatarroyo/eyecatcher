"""
Genome representation and serialization.

Generic NEAT genome: create_random_genome, genome_to_json, genome_from_json,
copy_genome. Dual-genome types and helpers live in substrate.dual_genome and
are exported from substrate.
"""

import neat

from .serialization import copy_genome, genome_from_json, genome_to_json


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


__all__ = [
    "create_random_genome",
    "copy_genome",
    "genome_from_json",
    "genome_to_json",
]

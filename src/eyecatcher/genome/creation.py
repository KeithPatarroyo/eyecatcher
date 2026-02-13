"""Create random NEAT genomes."""

import neat


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

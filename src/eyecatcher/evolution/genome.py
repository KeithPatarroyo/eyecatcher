"""
Genome types and creation: DualGenome and random genome creation.
"""

from typing import TYPE_CHECKING

import neat

if TYPE_CHECKING:
    from .engine import CPPNEngine


class DualGenome:
    """
    A paired genome consisting of a visual CPPN and a time signal CPPN.
    Both are evolved together with shared fitness.
    """

    __slots__ = ("visual", "time_signal", "key")

    def __init__(
        self,
        visual: neat.DefaultGenome,
        time_signal: neat.DefaultGenome,
        key: int = 0,
    ):
        self.visual = visual
        self.time_signal = time_signal
        self.key = key

    @property
    def fitness(self):
        """Return fitness (stored on visual genome)."""
        return self.visual.fitness

    @fitness.setter
    def fitness(self, value):
        """Set fitness on both genomes."""
        self.visual.fitness = value
        self.time_signal.fitness = value


def create_random_genome(config: neat.Config, genome_id: int = 0) -> neat.DefaultGenome:
    """
    Create a random genome with the given configuration.

    Args:
        config: NEAT configuration
        genome_id: ID for the genome

    Returns:
        Randomly initialized genome
    """
    genome = neat.DefaultGenome(genome_id)
    genome.configure_new(config.genome_config)
    return genome


def create_random_dual_genome(engine: "CPPNEngine", genome_id: int = 0) -> DualGenome:
    """
    Create a random dual genome (visual + time signal CPPNs).

    Args:
        engine: CPPNEngine instance with both configs loaded
        genome_id: ID for the dual genome

    Returns:
        Randomly initialized DualGenome
    """
    visual_genome = create_random_genome(engine.config, genome_id)
    time_genome = create_random_genome(engine.time_config, genome_id)
    return DualGenome(visual=visual_genome, time_signal=time_genome, key=genome_id)

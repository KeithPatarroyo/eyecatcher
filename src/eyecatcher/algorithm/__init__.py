"""
Evolution algorithm: config, reproduction, and optimization operators.

Core neuroevolution for CPPN and other substrates.
"""

from .config import (
    CROSSOVER_PROBABILITY,
    DEFAULT_NUM_FRAMES,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_TIME,
    MAX_POPULATION_SIZE,
    NEAT_CONFIG_PATH,
    NEAT_TIME_CONFIG_PATH,
    PREVIEW_RENDER_RESOLUTION,
)
from .operators import (
    crossover_dual_genomes,
    crossover_single_genomes,
    mutate_dual_genome,
    mutate_single_genome,
)
from .reproduction import produce_next_generation

__all__ = [
    "produce_next_generation",
    "mutate_single_genome",
    "mutate_dual_genome",
    "crossover_single_genomes",
    "crossover_dual_genomes",
    "NEAT_CONFIG_PATH",
    "NEAT_TIME_CONFIG_PATH",
    "DEFAULT_POPULATION_SIZE",
    "CROSSOVER_PROBABILITY",
    "MAX_POPULATION_SIZE",
    "DEFAULT_RENDER_RESOLUTION",
    "DEFAULT_RENDER_TIME",
    "PREVIEW_RENDER_RESOLUTION",
    "DEFAULT_NUM_FRAMES",
]

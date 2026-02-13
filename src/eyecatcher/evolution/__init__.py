"""
Evolution algorithm: config, reproduction, and optimization operators.

Core neuroevolution for CPPN and other substrates.
"""

from . import config
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
    get_configured_substrate,
    get_crossover_probability,
    get_elitism_default,
    get_max_population_size,
    get_population_size,
    update_runtime_config,
)
from .operators import crossover_genomes, mutate_genome
from .reproduction import produce_next_generation

__all__ = [
    "config",
    "produce_next_generation",
    "mutate_genome",
    "crossover_genomes",
    "get_configured_substrate",
    "NEAT_CONFIG_PATH",
    "NEAT_TIME_CONFIG_PATH",
    "DEFAULT_POPULATION_SIZE",
    "CROSSOVER_PROBABILITY",
    "MAX_POPULATION_SIZE",
    "DEFAULT_RENDER_RESOLUTION",
    "DEFAULT_RENDER_TIME",
    "PREVIEW_RENDER_RESOLUTION",
    "DEFAULT_NUM_FRAMES",
    "get_population_size",
    "get_max_population_size",
    "get_crossover_probability",
    "get_elitism_default",
    "update_runtime_config",
]

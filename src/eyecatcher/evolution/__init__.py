"""
Evolution algorithm: config, reproduction, and optimization operators.

Core neuroevolution for CPPN and other substrates.
"""

from . import config
from .config import (
    CROSSOVER_PROBABILITY,
    DEFAULT_POPULATION_SIZE,
    ELITISM_DEFAULT,
    MAX_POPULATION_SIZE,
    MIN_POPULATION_SIZE,
    get_crossover_probability,
    get_elitism_default,
    get_max_population_size,
    get_population_size,
    update_runtime_config,
)
from .experiment import (
    NEAT_CONFIG_PATH,
    NEAT_TIME_CONFIG_PATH,
    get_configured_substrate,
    warn_if_neat_pop_size_mismatch,
)
from .fitness import FITNESS_REGISTRY, get_fitness, list_fitness, register_fitness
from ..genome.operators import crossover_genomes, mutate_genome
from .reproduction import produce_next_generation
from .render_defaults import (
    DEFAULT_NUM_FRAMES,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_TIME,
    PREVIEW_RENDER_RESOLUTION,
)

__all__ = [
    "FITNESS_REGISTRY",
    "get_fitness",
    "list_fitness",
    "register_fitness",
    "config",
    "produce_next_generation",
    "mutate_genome",
    "crossover_genomes",
    "get_configured_substrate",
    "warn_if_neat_pop_size_mismatch",
    "NEAT_CONFIG_PATH",
    "NEAT_TIME_CONFIG_PATH",
    "DEFAULT_POPULATION_SIZE",
    "CROSSOVER_PROBABILITY",
    "MAX_POPULATION_SIZE",
    "MIN_POPULATION_SIZE",
    "ELITISM_DEFAULT",
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

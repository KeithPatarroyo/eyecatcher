"""
Evolution algorithm: reproduction and fitness.

Core neuroevolution for CPPN and other representations.
Experiment config and preset selection live in experiment/.
"""

from ..experiment import (
    CROSSOVER_PROBABILITY,
    DEFAULT_NUM_FRAMES,
    DEFAULT_POPULATION_SIZE,
    ELITISM_DEFAULT,
    MAX_POPULATION_SIZE,
    MIN_POPULATION_SIZE,
    NEAT_CONFIG_PATH,
    NEAT_TIME_CONFIG_PATH,
    PREVIEW_RENDER_RESOLUTION,
    get_configured_representation,
    get_crossover_probability,
    get_elitism_default,
    get_max_population_size,
    get_population_size,
    update_runtime_config,
    warn_if_neat_pop_size_mismatch,
)
from ..experiment.config import DEFAULT_RENDER_RESOLUTION, DEFAULT_RENDER_TIME
from ..genome.operators import crossover_genomes, mutate_genome
from .fitness import FITNESS_REGISTRY, get_fitness, list_fitness, register_fitness
from .reproduction import produce_next_generation

__all__ = [
    "FITNESS_REGISTRY",
    "get_fitness",
    "list_fitness",
    "register_fitness",
    "produce_next_generation",
    "mutate_genome",
    "crossover_genomes",
    "get_configured_representation",
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

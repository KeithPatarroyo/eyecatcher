"""
Evolution algorithm: reproduction and fitness.

Core neuroevolution for CPPN and other representations.
Experiment config and preset selection live in experiment/.
"""

from .fitness import FITNESS_REGISTRY, get_fitness, list_fitness, register_fitness
from .reproduction import produce_next_generation

__all__ = [
    "FITNESS_REGISTRY",
    "get_fitness",
    "list_fitness",
    "register_fitness",
    "produce_next_generation",
]

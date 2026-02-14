"""
Experiment configuration and preset selection.

Population/evolution parameters, render defaults, and representation
selection from config/experiments.json. Evolution algorithm (reproduction,
fitness) stays in evolution/.
"""

from .config import (
    DEFAULT_NUM_FRAMES,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_TIME,
    PREVIEW_RENDER_RESOLUTION,
    apply_preset,
    config,
    get_crossover_probability,
    get_elitism_default,
    get_max_population_size,
    get_population_size,
    update_runtime_config,
)
from .preset import (
    NEAT_CONFIG_PATH,
    NEAT_TIME_CONFIG_PATH,
    get_configured_representation,
    warn_if_neat_pop_size_mismatch,
)

__all__ = [
    "apply_preset",
    "config",
    "DEFAULT_NUM_FRAMES",
    "DEFAULT_RENDER_RESOLUTION",
    "DEFAULT_RENDER_TIME",
    "get_configured_representation",
    "get_crossover_probability",
    "get_elitism_default",
    "get_max_population_size",
    "get_population_size",
    "NEAT_CONFIG_PATH",
    "NEAT_TIME_CONFIG_PATH",
    "PREVIEW_RENDER_RESOLUTION",
    "update_runtime_config",
    "warn_if_neat_pop_size_mismatch",
]

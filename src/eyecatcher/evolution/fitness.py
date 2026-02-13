"""
Pluggable fitness registry for batch evolution.

Researchers register fitness functions by name. Each function receives
(individual, substrate) and returns a float. Substrate-specific fitness
can use substrate.evaluate, substrate.config/time_config when available.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

FITNESS_REGISTRY: dict[str, Callable[..., float]] = {}

# Shared constants for built-in fitness
SAMPLE_COORDS = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
COLOR_VARIANCE_MULTIPLIER = 10
TEMPORAL_VARIANCE_MULTIPLIER = 5
MEAN_COLOR_PENALTY = 0.5
MEAN_COLOR_LOW = 0.1
MEAN_COLOR_HIGH = 0.9
TEMPORAL_SAMPLES = [0.2, 0.5, 0.8]
BIT_COUNT_DIVISOR = 8.0


def register_fitness(name: str):
    """Decorator to register a fitness function."""

    def decorator(fn: Callable[..., float]):
        FITNESS_REGISTRY[name] = fn
        return fn

    return decorator


def get_fitness(name: str) -> Callable[..., float] | None:
    """Return the fitness function for the given name, or None."""
    return FITNESS_REGISTRY.get(name)


def list_fitness() -> list[str]:
    """Return sorted list of registered fitness names."""
    return sorted(FITNESS_REGISTRY.keys())


def _sample_rgb_at_coords(
    individual: Any, substrate: Any, time: float = 0.0
) -> list[list[float]]:
    """Return list of [r,g,b] samples at SAMPLE_COORDS via substrate.sample_rgb."""
    return substrate.sample_rgb(individual, SAMPLE_COORDS, time=time)


# ---------------------------------------------------------------------------
# Built-in fitness functions
# ---------------------------------------------------------------------------


@register_fitness("color_variance")
def fitness_color_variance(individual: Any, substrate: Any) -> float:
    """
    Color variety across spatial samples. Uses substrate.sample_rgb when available.
    """
    samples = _sample_rgb_at_coords(individual, substrate)
    if samples:
        return float(np.var(samples)) * COLOR_VARIANCE_MULTIPLIER
    if hasattr(individual, "rule"):
        return float(bin(individual.rule).count("1")) / BIT_COUNT_DIVISOR
    return 0.0


@register_fitness("temporal_variance")
def fitness_temporal_variance(individual: Any, substrate: Any) -> float:
    """
    Variation over time at center. Non-zero for substrates that vary output with time.
    """
    samples = []
    for t in TEMPORAL_SAMPLES:
        rgb_list = substrate.sample_rgb(individual, [(0.0, 0.0)], time=t)
        if rgb_list:
            samples.append(rgb_list[0])
    if not samples:
        return 0.0
    return float(np.var(samples)) * TEMPORAL_VARIANCE_MULTIPLIER


@register_fitness("combined")
def fitness_combined(individual: Any, substrate: Any) -> float:
    """
    Color + temporal variance; penalize mean color outside [0.1, 0.9] when sampling RGB.
    """
    color = fitness_color_variance(individual, substrate)
    temporal = fitness_temporal_variance(individual, substrate)
    fitness = color + temporal
    samples = _sample_rgb_at_coords(individual, substrate)
    if samples:
        mean_color = np.mean(samples)
        if mean_color < MEAN_COLOR_LOW or mean_color > MEAN_COLOR_HIGH:
            fitness *= MEAN_COLOR_PENALTY
    return fitness


@register_fitness("ca_symmetry")
def fitness_ca_symmetry(individual: Any, substrate: Any) -> float:
    """
    For CA: prefer rules that produce symmetric patterns.
    Uses substrate.evaluate to run the rule.
    """
    if not hasattr(individual, "rule"):
        return 0.0
    out = substrate.evaluate(individual, {})
    if out.output_type != "grid" or not hasattr(out.data, "shape"):
        return 0.0
    grid = np.asarray(out.data)
    if grid.ndim == 3:
        grid = grid[:, :, 0]
    if grid.ndim >= 2:
        _, w = grid.shape[:2]
        left = grid[:, : w // 2]
        right = grid[:, w // 2 :]
        if right.shape[1] != left.shape[1]:
            right = right[:, :-1]
        diff = left.astype(float) - np.flip(right, axis=1).astype(float)
        symmetry = 1.0 - np.mean(np.abs(diff))
        return float(np.clip(symmetry, 0, 1))
    return 0.0

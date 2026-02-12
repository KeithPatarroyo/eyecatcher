"""
Pluggable fitness registry for batch evolution.

Researchers register fitness functions by name. Each function receives
(individual, substrate) and returns a float. Substrate-specific fitness
can use substrate.evaluate, substrate.config/time_config when available.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from ..lib.math_utils import normalize_to_bipolar

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


def _sample_rgb_at_coords(individual: Any, substrate: Any) -> list[list[float]]:
    """Return list of [r,g,b] samples at SAMPLE_COORDS for CPPN substrates."""
    from ..genome import DualGenome
    from ..signals.signals import get_default_signal_values

    samples = []
    if hasattr(substrate, "time_config") and isinstance(individual, DualGenome):
        from ..evaluation.query import query_dual_cppn

        for x, y in SAMPLE_COORDS:
            inputs = {"x": x, "y": y, **get_default_signal_values(0.0)}
            r, g, b = query_dual_cppn(
                individual, substrate.config, substrate.time_config, inputs
            )
            samples.append([r, g, b])
        return samples
    if hasattr(substrate, "config"):
        from ..evaluation.query import query_visual_cppn

        sigs = get_default_signal_values(0.0)
        for x, y in SAMPLE_COORDS:
            inputs = {"x": x, "y": y, "time": 0.0, **sigs}
            r, g, b = query_visual_cppn(individual, substrate.config, inputs)
            samples.append([r, g, b])
    return samples


# ---------------------------------------------------------------------------
# Built-in fitness functions
# ---------------------------------------------------------------------------


@register_fitness("color_variance")
def fitness_color_variance(individual: Any, substrate: Any) -> float:
    """
    Color variety across spatial samples. Works for CPPN substrates with
    query_dual_cppn or query_visual_cppn (via substrate.config/time_config).
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
    Variation over time at center. Dual-CPPN only (uses time signal).
    """
    from ..genome import DualGenome

    if not hasattr(substrate, "time_config") or not isinstance(individual, DualGenome):
        return 0.0
    from ..evaluation.query import query_dual_cppn

    samples = []
    for t in TEMPORAL_SAMPLES:
        raw_t = normalize_to_bipolar(t)
        inputs = {
            "x": 0.0,
            "y": 0.0,
            "raw_time": raw_t,
            "mouse_speed": 0.0,
            "mouse_dist": 0.0,
            "activity": 0.0,
        }
        r, g, b = query_dual_cppn(
            individual, substrate.config, substrate.time_config, inputs
        )
        samples.append([r, g, b])
    return float(np.var(samples)) * TEMPORAL_VARIANCE_MULTIPLIER


@register_fitness("combined")
def fitness_combined(individual: Any, substrate: Any) -> float:
    """
    Color variance + temporal variance. Dual-CPPN default.
    """
    from ..genome import DualGenome

    color = fitness_color_variance(individual, substrate)
    temporal = fitness_temporal_variance(individual, substrate)
    fitness = color + temporal
    if hasattr(substrate, "time_config") and isinstance(individual, DualGenome):
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

"""
Pluggable fitness registry for batch evolution.

Researchers register fitness functions by name. Each function receives
(individual, representation) and returns a float. Representation-specific
fitness can use representation.express and representation.sensory_system to
adapt behaviour to the active representation's declared capabilities.
"""

from collections.abc import Callable
from typing import Any

import numpy as np

from ..representation.protocol import Representation

FITNESS_REGISTRY: dict[str, Callable[[Any, Representation[Any]], float]] = {}
# Optional metadata: compatible_output_types for logging mismatches
FITNESS_METADATA: dict[str, dict[str, Any]] = {}

# Shared constants for built-in fitness
SAMPLE_COORDS = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
COLOR_VARIANCE_MULTIPLIER = 10
TEMPORAL_VARIANCE_MULTIPLIER = 5
MEAN_COLOR_PENALTY = 0.5
MEAN_COLOR_LOW = 0.1
MEAN_COLOR_HIGH = 0.9
TEMPORAL_SAMPLES = [0.2, 0.5, 0.8]
BIT_COUNT_DIVISOR = 8.0


def _wrap_fitness_with_compatibility_check(
    name: str, fn: Callable[[Any, Representation[Any]], float]
) -> Callable[[Any, Representation[Any]], float]:
    """Wrap fn to log a warning when representation.output_type is not compatible."""

    def wrapped(individual: Any, rep: Representation[Any]) -> float:
        meta = FITNESS_METADATA.get(name)
        if meta and "compatible_output_types" in meta:
            allowed = meta["compatible_output_types"]
            out_type = rep.output_type
            if allowed and out_type not in allowed:
                import logging

                logging.getLogger(__name__).warning(
                    "Fitness %r is designed for output types %s; "
                    "representation %r has output_type %r.",
                    name,
                    allowed,
                    rep.id,
                    out_type,
                )
        return fn(individual, rep)

    return wrapped


def register_fitness(name: str, compatible_output_types: list[str] | None = None):
    """Register a fitness function. Optional compatible_output_types for warnings."""

    def decorator(fn: Callable[[Any, Representation[Any]], float]):
        if compatible_output_types is not None:
            FITNESS_METADATA[name] = {
                "compatible_output_types": compatible_output_types
            }
            wrapped = _wrap_fitness_with_compatibility_check(name, fn)
            FITNESS_REGISTRY[name] = wrapped
        else:
            FITNESS_REGISTRY[name] = fn
        return fn

    return decorator


def get_fitness(name: str) -> Callable[[Any, Representation[Any]], float] | None:
    """Return the fitness function for the given name, or None."""
    return FITNESS_REGISTRY.get(name)


def list_fitness() -> list[str]:
    """Return sorted list of registered fitness names."""
    return sorted(FITNESS_REGISTRY.keys())


def _sample_rgb_at_coords(
    individual: Any, representation: Representation[Any], time: float = 0.0
) -> list[list[float]]:
    """Return list of [r,g,b] samples at SAMPLE_COORDS via representation.sample_rgb."""
    return representation.sample_rgb(individual, SAMPLE_COORDS, time=time)


# ---------------------------------------------------------------------------
# Built-in fitness functions
# ---------------------------------------------------------------------------


@register_fitness("color_variance", compatible_output_types=["field", "image"])
def fitness_color_variance(
    individual: Any, representation: Representation[Any]
) -> float:
    """
    Color variety across spatial samples. Uses representation.sample_rgb.
    Returns 0 when there are no samples (e.g. grid-only representations).
    """
    samples = _sample_rgb_at_coords(individual, representation)
    if not samples:
        return 0.0
    return float(np.var(samples)) * COLOR_VARIANCE_MULTIPLIER


@register_fitness("temporal_variance", compatible_output_types=["field", "image"])
def fitness_temporal_variance(
    individual: Any, representation: Representation[Any]
) -> float:
    """
    Variation over time at center. Non-zero for representations that vary
    output with time.  Returns 0 for representations without temporal signals.
    """
    if not representation.sensory_system.has_category("temporal"):
        return 0.0
    samples = []
    for t in TEMPORAL_SAMPLES:
        rgb_list = representation.sample_rgb(individual, [(0.0, 0.0)], time=t)
        if rgb_list:
            samples.append(rgb_list[0])
    if not samples:
        return 0.0
    return float(np.var(samples)) * TEMPORAL_VARIANCE_MULTIPLIER


@register_fitness("combined", compatible_output_types=["field", "image"])
def fitness_combined(individual: Any, representation: Representation[Any]) -> float:
    """
    Color + temporal variance; penalize mean color outside [0.1, 0.9] when sampling RGB.
    """
    color = fitness_color_variance(individual, representation)
    temporal = fitness_temporal_variance(individual, representation)
    fitness = color + temporal
    samples = _sample_rgb_at_coords(individual, representation)
    if samples:
        mean_color = np.mean(samples)
        if mean_color < MEAN_COLOR_LOW or mean_color > MEAN_COLOR_HIGH:
            fitness *= MEAN_COLOR_PENALTY
    return fitness


@register_fitness("ca_symmetry", compatible_output_types=["grid"])
def fitness_ca_symmetry(individual: Any, representation: Representation[Any]) -> float:
    """
    For CA: prefer rules that produce symmetric patterns.
    Uses representation.express and get_grid_for_symmetry.
    """
    out = representation.express(individual, {})
    grid = representation.get_grid_for_symmetry(out)
    if grid is None:
        return 0.0
    _, w = grid.shape[:2]
    left = grid[:, : w // 2]
    right = grid[:, w // 2 :]
    if right.shape[1] != left.shape[1]:
        right = right[:, :-1]
    diff = left.astype(float) - np.flip(right, axis=1).astype(float)
    symmetry = 1.0 - np.mean(np.abs(diff))
    return float(np.clip(symmetry, 0, 1))


# ---------------------------------------------------------------------------
# NCA fitness functions
# ---------------------------------------------------------------------------


@register_fitness("nca_alive_count", compatible_output_types=["grid"])
def fitness_nca_alive_count(
    individual: Any, representation: Representation[Any]
) -> float:
    """
    Reward NCA/grid for having a moderate number of alive cells.
    Penalize collapse (too few) and explosion (too many).
    """
    out = representation.express(individual, {})
    grid = representation.get_grid_for_symmetry(out)
    if grid is None:
        return 0.0
    alive = np.sum(grid > 0)
    total = grid.size
    if total == 0:
        return 0.0
    ratio = alive / total
    if ratio < 0.01:
        return 0.0
    if ratio > 0.95:
        return 0.0
    return float(ratio * (1.0 - ratio))


@register_fitness("nca_growth_stability", compatible_output_types=["grid"])
def fitness_nca_growth_stability(
    individual: Any, representation: Representation[Any]
) -> float:
    """
    Reward NCA that produce similar patterns at different step counts (stable growth).
    """
    steps_short = 24
    steps_long = 48
    out_short = representation.express(individual, {}, nca_steps=steps_short)
    out_long = representation.express(individual, {}, nca_steps=steps_long)
    g_short = representation.get_grid_for_symmetry(out_short)
    g_long = representation.get_grid_for_symmetry(out_long)
    if g_short is None or g_long is None:
        return 0.0
    g_short = np.asarray(g_short).astype(float)
    g_long = np.asarray(g_long).astype(float)
    if g_short.shape != g_long.shape:
        return 0.0
    diff = np.mean(np.abs(g_short - g_long))
    return float(np.clip(1.0 - diff, 0, 1))


@register_fitness("nca_symmetry", compatible_output_types=["grid"])
def fitness_nca_symmetry(individual: Any, representation: Representation[Any]) -> float:
    """Same as ca_symmetry: prefer symmetric patterns (NCA or CA)."""
    return fitness_ca_symmetry(individual, representation)

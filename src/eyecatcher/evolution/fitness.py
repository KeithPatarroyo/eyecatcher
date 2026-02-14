"""
Pluggable fitness registry for batch evolution.

Researchers register fitness functions by name. Each function receives
(individual, representation) and returns a float. Representation-specific
fitness can use representation.express and representation.signal_spec to
adapt behaviour to the active representation's declared capabilities.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from ..signals.spec import SignalSpec

FITNESS_REGISTRY: dict[str, Callable[..., float]] = {}
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
    name: str, fn: Callable[..., float]
) -> Callable[..., float]:
    """Wrap fn to log a warning when representation.output_type is not compatible."""

    def wrapped(individual: Any, rep: Any) -> float:
        meta = FITNESS_METADATA.get(name)
        if meta and "compatible_output_types" in meta:
            allowed = meta["compatible_output_types"]
            out_type = getattr(rep.__class__, "output_type", None)
            if out_type is not None and allowed and out_type not in allowed:
                import logging

                logging.getLogger(__name__).warning(
                    "Fitness %r is designed for output types %s; "
                    "representation %r has output_type %r.",
                    name,
                    allowed,
                    getattr(rep, "id", rep.__class__.__name__),
                    out_type,
                )
        return fn(individual, rep)

    return wrapped


def register_fitness(name: str, compatible_output_types: list[str] | None = None):
    """Register a fitness function. Optional compatible_output_types for warnings."""

    def decorator(fn: Callable[..., float]):
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


def get_fitness(name: str) -> Callable[..., float] | None:
    """Return the fitness function for the given name, or None."""
    return FITNESS_REGISTRY.get(name)


def list_fitness() -> list[str]:
    """Return sorted list of registered fitness names."""
    return sorted(FITNESS_REGISTRY.keys())


def _get_signal_spec(representation: Any) -> SignalSpec | None:
    """Return the representation's signal_spec, or None if absent."""
    return getattr(representation, "signal_spec", None)


def _has_temporal_signals(representation: Any) -> bool:
    """True if the representation declares temporal input signals."""
    spec = _get_signal_spec(representation)
    if spec is None:
        return True  # no spec: assume temporal for backward compatibility
    return any(s.category == "temporal" for s in spec.inputs)


def _sample_rgb_at_coords(
    individual: Any, representation: Any, time: float = 0.0
) -> list[list[float]]:
    """Return list of [r,g,b] samples at SAMPLE_COORDS via representation.sample_rgb."""
    return representation.sample_rgb(individual, SAMPLE_COORDS, time=time)


# ---------------------------------------------------------------------------
# Built-in fitness functions
# ---------------------------------------------------------------------------


@register_fitness("color_variance", compatible_output_types=["shader", "image"])
def fitness_color_variance(individual: Any, representation: Any) -> float:
    """
    Color variety across spatial samples. Uses representation.sample_rgb when available.
    """
    samples = _sample_rgb_at_coords(individual, representation)
    if samples:
        return float(np.var(samples)) * COLOR_VARIANCE_MULTIPLIER
    if hasattr(individual, "rule"):
        return float(bin(individual.rule).count("1")) / BIT_COUNT_DIVISOR
    return 0.0


@register_fitness("temporal_variance", compatible_output_types=["shader", "image"])
def fitness_temporal_variance(individual: Any, representation: Any) -> float:
    """
    Variation over time at center. Non-zero for representations that vary
    output with time.  Returns 0 for representations without temporal signals.
    """
    if not _has_temporal_signals(representation):
        return 0.0
    samples = []
    for t in TEMPORAL_SAMPLES:
        rgb_list = representation.sample_rgb(individual, [(0.0, 0.0)], time=t)
        if rgb_list:
            samples.append(rgb_list[0])
    if not samples:
        return 0.0
    return float(np.var(samples)) * TEMPORAL_VARIANCE_MULTIPLIER


@register_fitness("combined", compatible_output_types=["shader", "image"])
def fitness_combined(individual: Any, representation: Any) -> float:
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
def fitness_ca_symmetry(individual: Any, representation: Any) -> float:
    """
    For CA: prefer rules that produce symmetric patterns.
    Uses representation.express to run the rule.
    """
    if not hasattr(individual, "rule"):
        return 0.0
    out = representation.express(individual, {})
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

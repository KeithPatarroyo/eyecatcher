"""
Pluggable fitness registry for batch evolution.

Researchers register fitness functions by name. Each function receives
(individual, substrate) and returns a float. Substrate-specific fitness
can use substrate.evaluate, substrate.engine (when available), or custom logic.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

FITNESS_REGISTRY: dict[str, Callable[..., float]] = {}


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


# ---------------------------------------------------------------------------
# Built-in fitness functions
# ---------------------------------------------------------------------------


@register_fitness("color_variance")
def fitness_color_variance(individual: Any, substrate: Any) -> float:
    """
    Color variety across spatial samples. Works for CPPN substrates with
    engine.query_dual_cppn or query_visual_cppn.
    """
    from ..genome import DualGenome
    from ..signals.signals import get_default_signal_values

    engine = getattr(substrate, "engine", None)
    if engine is not None and isinstance(individual, DualGenome):
        coords = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
        samples = []
        for x, y in coords:
            inputs = {"x": x, "y": y, **get_default_signal_values(0.0)}
            r, g, b = engine.query_dual_cppn(individual, inputs)
            samples.append([r, g, b])
        return float(np.var(samples)) * 10
    if hasattr(substrate, "config"):
        from ..evaluation.query import query_visual_cppn

        coords = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
        samples = []
        sigs = get_default_signal_values(0.0)
        for x, y in coords:
            inputs = {"x": x, "y": y, "time": 0.0, **sigs}
            r, g, b = query_visual_cppn(individual, substrate.config, inputs)
            samples.append([r, g, b])
        return float(np.var(samples)) * 10
    if hasattr(individual, "rule"):
        return float(bin(individual.rule).count("1")) / 8.0
    return 0.0


@register_fitness("temporal_variance")
def fitness_temporal_variance(individual: Any, substrate: Any) -> float:
    """
    Variation over time at center. Dual-CPPN only (uses time signal).
    """
    engine = getattr(substrate, "engine", None)
    if engine is None:
        return 0.0
    from ..genome import DualGenome

    if not isinstance(individual, DualGenome):
        return 0.0
    times = [0.2, 0.5, 0.8]
    samples = []
    for t in times:
        raw_t = -1.0 + t * 2.0
        inputs = {
            "x": 0.0,
            "y": 0.0,
            "raw_time": raw_t,
            "mouse_speed": 0.0,
            "mouse_dist": 0.0,
            "activity": 0.0,
        }
        r, g, b = engine.query_dual_cppn(individual, inputs)
        samples.append([r, g, b])
    return float(np.var(samples)) * 5


@register_fitness("combined")
def fitness_combined(individual: Any, substrate: Any) -> float:
    """
    Color variance + temporal variance. Dual-CPPN default.
    """
    color = fitness_color_variance(individual, substrate)
    temporal = fitness_temporal_variance(individual, substrate)
    fitness = color + temporal
    engine = getattr(substrate, "engine", None)
    if engine is not None:
        from ..genome import DualGenome

        if isinstance(individual, DualGenome):
            from ..signals.signals import get_default_signal_values

            coords = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
            samples = []
            for x, y in coords:
                inputs = {"x": x, "y": y, **get_default_signal_values(0.0)}
                r, g, b = engine.query_dual_cppn(individual, inputs)
                samples.append([r, g, b])
            mean_color = np.mean(samples)
            if mean_color < 0.1 or mean_color > 0.9:
                fitness *= 0.5
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

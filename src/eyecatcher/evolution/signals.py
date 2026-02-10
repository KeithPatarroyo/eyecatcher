"""Central registry of CPPN input and output signals.

Defines VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS, TIME_OUTPUTS so that
query, glsl (shader compiler), serialization, and genome_visualizer consume one
source of truth. To add/rename a signal, edit this file and
static/js/modules/evolution_config.js; update NEAT num_inputs/num_outputs
(and frontend SIGNAL_TOGGLES for toggleable inputs).

Derived inputs: some signals are computed from other inputs when not provided
(e.g. distance = sqrt(x² + y²)). Register them in VISUAL_DERIVED_INPUTS so
query logic can fill them without special-case code.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Signal:
    """Single CPPN input signal."""

    name: str  # internal id, e.g. "mouse_speed"
    glsl_var: str  # GLSL variable name, e.g. "vMouseSpeed"
    uniform: str  # JS uniform name, e.g. "uMouseSpeed" (empty for spatial/bias)
    enable_key: str  # JS camelCase key, e.g. "mouseSpeed" (empty for spatial/bias)
    label: str  # human-readable, e.g. "Mouse Speed"
    default: float  # neutral value (0.0 usually; 1.0 for bias)
    is_spatial: bool  # True for x, y, distance (per-pixel, no uniform)


@dataclass(frozen=True)
class Output:
    """Single CPPN output."""

    name: str  # e.g. "red"
    label: str  # e.g. "Red"


# Visual CPPN: 8 inputs (x, y, distance, time, mouse_speed, mouse_distance,
# inactivity, bias)
VISUAL_INPUTS: list[Signal] = [
    Signal("x", "vX", "", "", "x", 0.0, True),
    Signal("y", "vY", "", "", "y", 0.0, True),
    Signal("distance", "vDist", "", "", "distance", 0.0, True),
    Signal("time", "vTime", "", "time", "Time", 0.0, False),
    Signal(
        "mouse_speed",
        "vMouseSpeed",
        "uMouseSpeed",
        "mouseSpeed",
        "Mouse Speed",
        0.0,
        False,
    ),
    Signal(
        "mouse_distance",
        "vMouseDist",
        "uMouseDist",
        "mouseDist",
        "Mouse Dist",
        0.0,
        False,
    ),
    Signal(
        "inactivity",
        "vInactivity",
        "uInactivity",
        "inactivity",
        "Activity",
        0.0,
        False,
    ),
    Signal("bias", "vBias", "", "", "bias", 1.0, False),
]

# Time signal CPPN: 5 inputs (raw_time, mouse_speed, mouse_distance, inactivity, bias)
TIME_INPUTS: list[Signal] = [
    Signal("raw_time", "vRawTime", "uTime", "rawTime", "Raw Time", 0.0, False),
    Signal(
        "mouse_speed",
        "vMouseSpeed",
        "uMouseSpeed",
        "mouseSpeed",
        "Mouse Speed",
        0.0,
        False,
    ),
    Signal(
        "mouse_distance",
        "vMouseDist",
        "uMouseDist",
        "mouseDist",
        "Mouse Dist",
        0.0,
        False,
    ),
    Signal(
        "inactivity",
        "vInactivity",
        "uInactivity",
        "inactivity",
        "Activity",
        0.0,
        False,
    ),
    Signal("bias", "vBias", "", "", "bias", 1.0, False),
]

VISUAL_OUTPUTS: list[Output] = [
    Output("red", "Red"),
    Output("green", "Green"),
    Output("blue", "Blue"),
]

TIME_OUTPUTS: list[Output] = [
    Output("output", "Modified Time"),
]

# Map network_type to (inputs, outputs) for extract_network_data and similar.
NETWORK_SIGNALS: dict[str, tuple[list[Signal], list[Output]]] = {
    "visual": (VISUAL_INPUTS, VISUAL_OUTPUTS),
    "time": (TIME_INPUTS, TIME_OUTPUTS),
}

# Names for the time-related input in each CPPN (avoid repeated lookups).
VISUAL_TIME_INPUT_NAME: str = next(
    s.name for s in VISUAL_INPUTS if s.enable_key == "time"
)
TIME_CPPN_TIME_INPUT_NAME: str = TIME_INPUTS[0].name

# Derived inputs: computed from other inputs when not provided.
# List of (output_signal_name, (dependency_names, ...), compute_fn).
# compute_fn(*values) receives dependency values in order.
# Only fill if the output key is missing and all dependencies are present.
VISUAL_DERIVED_INPUTS: list[tuple[str, tuple[str, ...], Callable[..., float]]] = [
    ("distance", ("x", "y"), lambda x, y: math.sqrt(x * x + y * y)),
]


def apply_derived_inputs(values: dict[str, float], derived: list) -> None:
    """Fill in derived signal values when dependencies are present. Mutates values."""
    for name, deps, fn in derived:
        if name in values:
            continue
        if all(d in values for d in deps):
            values[name] = float(fn(*[values[d] for d in deps]))


def input_labels(signals: Sequence[Signal]) -> list[str]:
    """Return label strings for a list of signals (for serialization/display)."""
    return [s.label for s in signals]


def output_labels(outputs: Sequence[Output]) -> list[str]:
    """Return label strings for a list of outputs (for display)."""
    return [o.label for o in outputs]


def output_names(outputs: Sequence[Output]) -> list[str]:
    """Return name strings for outputs (serialization)."""
    return [o.name for o in outputs]


def input_names(signals: Sequence[Signal]) -> list[str]:
    """Return name strings for inputs (serialization, genome_visualizer)."""
    return [s.name for s in signals]


def build_glsl_input_map(signals: Sequence[Signal]) -> dict:
    """
    Build dict mapping NEAT negative node IDs to GLSL variable names.

    First signal gets most-negative ID (e.g. 8 inputs -> -8..-1).
    """
    n = len(signals)
    return {-n + i: signals[i].glsl_var for i in range(n)}


def inputs_array(signals: Sequence[Signal], values: dict) -> list[float]:
    """
    Build the input array for a CPPN from a dict of signal name -> value.

    Missing keys use Signal.default. Use this so adding a new signal only
    requires extending the registry; callers pass optional keys when available.
    """
    return [values.get(s.name, s.default) for s in signals]


def default_inputs(signals: Sequence[Signal]) -> dict[str, float]:
    """Return a dict of signal name -> default value for all signals."""
    return {s.name: s.default for s in signals}

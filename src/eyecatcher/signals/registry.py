"""Central registry of network input and output signals.

**Scope: dual-CPPN-centric.** The names VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS,
TIME_OUTPUTS reflect the dual-CPPN architecture (one visual network, one time-signal
network). Single-CPPN and CA representations use only a subset (e.g. VISUAL_* for
single CPPN; CA uses neither). Other representations (e.g. NCA, different topologies)
may reuse these as building blocks or ignore them and define their own signal sets.

**Extending for new representations:** If you add a representation that needs
different inputs/outputs, either (1) compose from existing lists where it makes
sense, or (2) define representation-specific signal lists in your module and use
them in your representation's config/query/GLSL logic. The registry here remains
the single source for dual-CPPN and for any shared signals; representations can
declare additional signals locally.

Defines VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS, TIME_OUTPUTS so that
query, glsl (shader compiler), serialization, and genome_visualizer consume one
source of truth. Run scripts/generate_signal_config.py to emit JS config and
validate NEAT; update NEAT num_inputs/num_outputs when counts change.

Derived inputs: some signals are computed from other inputs when not provided
(e.g. distance = sqrt(x² + y²)). Register them in VISUAL_DERIVED_INPUTS so
query logic can fill them without special-case code.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

# Ids that get their value from another network (e.g. visual "time" from time net).
# Used only for export/UI; not a Signal field.
_DERIVED_IDS: frozenset[str] = frozenset({"time"})


def _is_toggleable(s: Signal) -> bool:
    """True if this signal has a value uniform (not spatial, not bias)."""
    return not s.is_spatial and s.id != "bias"


@dataclass(frozen=True)
class Signal:
    """Network input signal. id used everywhere; GLSL gets u_/v_ prefix in compiler."""

    id: str
    label: str
    default: float = 0.0
    is_spatial: bool = False

    def _uniform(self) -> str:
        return f"u_{self.id}" if _is_toggleable(self) else ""

    def _glsl_var(self) -> str:
        return f"v_{self.id}"

    def _is_derived(self) -> bool:
        return self.id in _DERIVED_IDS


@dataclass(frozen=True)
class Output:
    """Single network output."""

    id: str
    label: str


# Visual network inputs (x, y, distance, time, mouse_*, activity, mouse_x/y, bias)
VISUAL_INPUTS: list[Signal] = [
    Signal("x", "x", 0.0, True),
    Signal("y", "y", 0.0, True),
    Signal("distance", "distance", 0.0, True),
    Signal("time", "Time", 0.0, False),  # derived from time signal network
    Signal("mouse_speed", "Mouse Speed"),
    Signal("mouse_dist", "Mouse Dist"),
    Signal("activity", "Activity"),
    Signal("mouse_x", "Mouse X"),
    Signal("mouse_y", "Mouse Y"),
    Signal("bias", "Bias", 1.0),
]

# Time signal network inputs (raw_time, mouse_speed, mouse_dist, activity, bias)
TIME_INPUTS: list[Signal] = [
    Signal("raw_time", "Raw Time"),
    Signal("mouse_speed", "Mouse Speed"),
    Signal("mouse_dist", "Mouse Dist"),
    Signal("activity", "Activity"),
    Signal("bias", "Bias", 1.0),
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

VISUAL_TIME_INPUT_NAME: str = "time"
TIME_CPPN_TIME_INPUT_NAME: str = TIME_INPUTS[0].id


@dataclass(frozen=True)
class DerivedInput:
    """Derived spatial input: id, dependencies, Python compute fn, and GLSL snippet."""

    id: str
    deps: tuple[str, ...]
    compute: Callable[..., float]
    glsl: str  # GLSL line(s) computing v_{id} from v_{dep} / u_{dep} vars


# Derived inputs: computed from other inputs when not provided.
# Single source of truth for Python evaluation and GLSL generation.
VISUAL_DERIVED_INPUTS: list[DerivedInput] = [
    DerivedInput(
        id="distance",
        deps=("x", "y"),
        compute=lambda x, y: math.sqrt(x * x + y * y),
        glsl="float v_distance = sqrt(v_x * v_x + v_y * v_y);",
    ),
]


def apply_derived_inputs(values: dict[str, float], derived: list) -> None:
    """Fill in derived signal values when dependencies are present. Mutates values."""
    for d in derived:
        if d.id in values:
            continue
        if all(dep in values for dep in d.deps):
            values[d.id] = float(d.compute(*[values[dep] for dep in d.deps]))


def input_labels(signals: Sequence[Signal]) -> list[str]:
    """Return label strings for a list of signals (for serialization/display)."""
    return [s.label for s in signals]


def output_labels(outputs: Sequence[Output]) -> list[str]:
    """Return label strings for a list of outputs (for display)."""
    return [o.label for o in outputs]


def input_names(signals: Sequence[Signal]) -> list[str]:
    """Return id strings for inputs (serialization, genome_visualizer)."""
    return [s.id for s in signals]


def build_glsl_input_map(signals: Sequence[Signal]) -> dict:
    """
    Build dict mapping NEAT negative node IDs to GLSL variable names.

    First signal gets most-negative ID.
    """
    n = len(signals)
    return {-n + i: signals[i]._glsl_var() for i in range(n)}


def inputs_array(signals: Sequence[Signal], values: dict) -> list[float]:
    """
    Build the input array for a network from a dict of signal id -> value.

    Missing keys use Signal.default. Viewer sends keys matching signal ids.
    """
    return [values.get(s.id, s.default) for s in signals]


def default_inputs(signals: Sequence[Signal]) -> dict[str, float]:
    """Return a dict of signal id -> default value for all signals."""
    return {s.id: s.default for s in signals}


def parse_time_inputs(data: dict, bipolar: bool = False) -> dict[str, float]:
    """
    Build TIME_INPUTS dict from request-like data. Handles raw_time/time alias.
    When bipolar=True, values are scaled to [-1, 1] (e.g. for NEAT input).
    """
    out = {}
    for s in TIME_INPUTS:
        raw_val = data.get(s.id)
        if raw_val is None and s.id == "raw_time":
            raw_val = data.get("time")
        val = float(raw_val if raw_val is not None else s.default)
        out[s.id] = (val * 2.0 - 1.0) if bipolar else val
    return out


def get_viewer_signal_ids() -> list[str]:
    """Viewer (or pluggable source) ids. Same set as export_for_frontend SIGNAL_IDS."""
    seen: set[str] = set()
    for s in TIME_INPUTS:
        if _is_toggleable(s):
            seen.add(s.id)
    for s in VISUAL_INPUTS:
        if _is_toggleable(s) and not s._is_derived():
            seen.add(s.id)
    return sorted(seen)


def get_default_signal_values(
    time: float = 0.5, **overrides: float
) -> dict[str, float]:
    """Default signal values for headless/batch. Keys match get_viewer_signal_ids()."""
    result = {sid: 0.0 for sid in get_viewer_signal_ids()}
    result["raw_time"] = time
    result.update(overrides)
    return result


def export_for_frontend() -> dict:
    """Export signal config for JS. Used by generate_signal_config.py.

    Returns a dict with SIGNAL_TOGGLES (time + visual toggleableInputs),
    OUTPUTS (visual + time), and SIGNAL_IDS (ids that need values from viewer).
    """

    def toggleable_inputs(signals: list[Signal]) -> list[dict]:
        out = []
        for s in signals:
            if not _is_toggleable(s):
                continue
            entry = {
                "id": s.id,
                "label": s.label,
                "uniform": s._uniform() or None,
            }
            if s._is_derived():
                entry["derived"] = True
            out.append(entry)
        return out

    return {
        "SIGNAL_TOGGLES": {
            "time": {"toggleableInputs": toggleable_inputs(TIME_INPUTS)},
            "visual": {"toggleableInputs": toggleable_inputs(VISUAL_INPUTS)},
        },
        "OUTPUTS": {
            "visual": [{"id": o.id, "label": o.label} for o in VISUAL_OUTPUTS],
            "time": [{"id": o.id, "label": o.label} for o in TIME_OUTPUTS],
        },
        "SIGNAL_IDS": get_viewer_signal_ids(),
    }

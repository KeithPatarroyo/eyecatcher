"""Signal helpers: parameterized on SignalSpec or signal lists.

Canonical definitions live in spec (primitives, SignalSpec) and catalog
(concrete instances and presets). This module provides functions that
operate on them; all require explicit spec or signal list arguments.
"""

from __future__ import annotations

from collections.abc import Sequence

from .spec import (
    DerivedInput,
    Output,
    Signal,
    SignalSpec,
    _is_toggleable,
    apply_derived_inputs,
    build_glsl_input_map,
    default_inputs,
    input_labels,
    input_names,
    inputs_array,
    output_labels,
)


def parse_time_inputs(
    data: dict,
    signals: Sequence[Signal],
    bipolar: bool = False,
) -> dict[str, float]:
    """Build signal dict from request-like data.

    Parameters
    ----------
    data:
        Mapping of signal id -> raw value (from viewer / request).
    signals:
        Signal list to iterate (e.g. representation time inputs).
    bipolar:
        When True, values are scaled to [-1, 1] for NEAT input.
    """
    out: dict[str, float] = {}
    for s in signals:
        raw_val = data.get(s.id)
        val = float(raw_val if raw_val is not None else s.default)
        out[s.id] = (val * 2.0 - 1.0) if bipolar else val
    return out


def get_viewer_signal_ids(spec: SignalSpec) -> list[str]:
    """Signal ids that the viewer must supply, from the representation's spec."""
    seen: set[str] = set()
    for s in spec.inputs:
        if _is_toggleable(s) and not s._is_derived():
            seen.add(s.id)
    return sorted(seen)


def get_default_signal_values(
    spec: SignalSpec,
    time: float = 0.5,
    **overrides: float,
) -> dict[str, float]:
    """Default signal values for headless / batch rendering."""
    result = {sid: 0.0 for sid in get_viewer_signal_ids(spec)}
    for s in spec.inputs:
        if s.category == "temporal" and not s._is_derived():
            result[s.id] = time
            break
    result.update(overrides)
    return result


def _toggleable_entry(s: Signal) -> dict:
    """Single toggleable signal entry for frontend export."""
    entry: dict = {
        "id": s.id,
        "label": s.label,
        "uniform": s._uniform() or None,
    }
    if s._is_derived():
        entry["derived"] = True
    return entry


_CATEGORY_LABELS = {
    "spatial": "Spatial",
    "temporal": "Temporal",
    "interaction": "Interaction",
    "structural": "Structural",
    "other": "Other",
}


def export_for_frontend(spec: SignalSpec) -> dict:
    """Export signal config for JS: flat TOGGLEABLE_SIGNALS and SIGNAL_GROUPS for UI.

    Groups are auto-derived from Signal.category (no manual groups dict needed).
    """
    toggleable_list = [_toggleable_entry(s) for s in spec.inputs if _is_toggleable(s)]

    by_cat: dict[str, list] = {}
    for s in spec.inputs:
        if not _is_toggleable(s):
            continue
        cat = s.category or "other"
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(_toggleable_entry(s))
    signal_groups = [
        {"label": _CATEGORY_LABELS.get(c, c), "signals": sigs}
        for c, sigs in sorted(by_cat.items())
    ]

    return {
        "SIGNAL_GROUPS": signal_groups,
        "TOGGLEABLE_SIGNALS": toggleable_list,
        "SIGNAL_IDS": get_viewer_signal_ids(spec),
        "OUTPUTS": [{"id": o.id, "label": o.label} for o in spec.outputs],
    }


__all__ = [
    "Signal",
    "Output",
    "DerivedInput",
    "SignalSpec",
    "_is_toggleable",
    "apply_derived_inputs",
    "build_glsl_input_map",
    "default_inputs",
    "export_for_frontend",
    "get_default_signal_values",
    "get_viewer_signal_ids",
    "input_labels",
    "input_names",
    "inputs_array",
    "output_labels",
    "parse_time_inputs",
]

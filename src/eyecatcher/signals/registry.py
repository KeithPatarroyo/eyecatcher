"""Signal helpers: parameterized on SensorySystem or signal lists.

Canonical definitions live in sensory_system (primitives, SensorySystem) and catalog
(concrete instances and presets). This module provides functions that
operate on them; all require explicit sensory_system or signal list arguments.
"""

from collections.abc import Sequence

from .sensory_system import (
    SensorySystem,
    Signal,
    _is_toggleable,
    apply_derived_inputs,
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


def get_viewer_signal_ids(env: SensorySystem) -> list[str]:
    """Signal ids from representation.sensory_system that the viewer must supply."""
    seen: set[str] = set()
    for s in env.inputs:
        if _is_toggleable(s) and not s._is_derived():
            seen.add(s.id)
    return sorted(seen)


def get_default_signal_values(
    env: SensorySystem,
    time: float = 0.5,
    **overrides: float,
) -> dict[str, float]:
    """Default signal values for headless / batch rendering."""
    result = {sid: 0.0 for sid in get_viewer_signal_ids(env)}
    for s in env.inputs:
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
        "uniform": ("u_" + s.id) if _is_toggleable(s) else None,
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


def export_for_frontend(env: SensorySystem) -> dict:
    """Export signal config for JS: flat TOGGLEABLE_SIGNALS and SIGNAL_GROUPS for UI.

    Groups are auto-derived from Signal.category (no manual groups dict needed).
    """
    toggleable_list = [_toggleable_entry(s) for s in env.inputs if _is_toggleable(s)]

    by_cat: dict[str, list] = {}
    for s in env.inputs:
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
        "SIGNAL_IDS": get_viewer_signal_ids(env),
        "OUTPUTS": [{"id": o.id, "label": o.label} for o in env.outputs],
    }


__all__ = [
    "apply_derived_inputs",
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

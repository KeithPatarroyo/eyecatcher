"""Export representation metadata for frontend codegen.

generate_representation_config.py → config.generated.js. Uses
frontend_metadata and representation.capabilities.
"""

from __future__ import annotations

from ..signals.spec import SignalSpec, _is_toggleable
from .registry import REPRESENTATIONS, get_representation


def _capabilities_to_frontend(caps: dict[str, bool]) -> dict[str, bool]:
    """Convert snake_case capability keys to frontend camelCase."""
    return {
        "save": caps.get("save", False),
        "network": caps.get("network", False),
        "timeOutput": caps.get("time_output", False),
        "adjustWeight": caps.get("adjust_weight", False),
    }


def _signal_spec_to_frontend(spec: SignalSpec) -> dict:
    """Serialize a SignalSpec for the frontend."""
    inputs = []
    for s in spec.inputs:
        entry: dict = {"id": s.id, "label": s.label, "default": s.default}
        if s.is_spatial:
            entry["isSpatial"] = True
        if _is_toggleable(s):
            entry["uniform"] = s._uniform()
        if s._is_derived():
            entry["derived"] = True
        inputs.append(entry)

    outputs = [{"id": o.id, "label": o.label} for o in spec.outputs]

    derived = []
    for d in spec.derived_inputs:
        derived.append({"id": d.id, "deps": list(d.deps), "glsl": d.glsl})

    return {
        "inputs": inputs,
        "outputs": outputs,
        "derivedInputs": derived,
    }


def export_representations_for_frontend() -> list[dict]:
    """
    Return per-representation config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys,
    capabilities, signalSpec.  Signal specs are representation-agnostic
    declarations of what each representation accepts and produces.
    """
    result = []
    for rid in REPRESENTATIONS:
        rep = get_representation(rid)
        entry = rep.frontend_metadata
        if not isinstance(entry, dict):
            entry = {}
        caps = dict(rep.capabilities)
        rep_data: dict = {
            "id": rid,
            "outputType": rep.output_type,
            **entry,
            "capabilities": _capabilities_to_frontend(caps),
        }
        spec = rep.signal_spec
        rep_data["signalSpec"] = _signal_spec_to_frontend(spec)
        result.append(rep_data)
    return result

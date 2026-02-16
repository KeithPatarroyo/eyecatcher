"""Export representation metadata for frontend codegen.

Unified scripts/generate_config.py writes static/js/config.generated.js.
Uses frontend_metadata and representation.capabilities.
"""

from ..signals.sensory_system import SensorySystem, _is_toggleable
from .protocol import Behaviour, Phenotype, Substrate
from .registry import REPRESENTATIONS, get_representation


def _substrate_to_frontend(s: Substrate) -> dict:
    """Serialize Substrate for the frontend (camelCase)."""
    out: dict = {"type": s.type}
    if s.grid_size is not None:
        out["gridSize"] = s.grid_size
    if s.state_format is not None:
        out["stateFormat"] = s.state_format
    if s.wrap is not None:
        out["wrap"] = s.wrap
    return out


def _behaviour_to_frontend(b: Behaviour) -> dict:
    """Serialize Behaviour for the frontend (camelCase)."""
    out: dict = {}
    if b.update_rule is not None:
        out["updateRule"] = b.update_rule
    if b.update_interval_ms is not None:
        out["updateIntervalMs"] = b.update_interval_ms
    if b.interaction_rule is not None:
        out["interactionRule"] = b.interaction_rule
    if b.interactions:
        out["interactions"] = list(b.interactions)
    return out


def _phenotype_to_frontend(p: Phenotype) -> dict:
    """Serialize a Phenotype for the frontend (camelCase keys, omit None)."""
    out: dict = {"substrate": _substrate_to_frontend(p.substrate)}
    if p.display_rule is not None:
        out["displayRule"] = p.display_rule
    if p.meta_template is not None:
        out["metaTemplate"] = p.meta_template
    if (
        p.behaviour.update_rule
        or p.behaviour.interaction_rule
        or p.behaviour.interactions
    ):
        out["behaviour"] = _behaviour_to_frontend(p.behaviour)
    return out


def _capabilities_to_frontend(caps: dict[str, bool]) -> dict[str, bool]:
    """Convert snake_case capability keys to frontend camelCase."""
    return {
        "save": caps.get("save", False),
        "network": caps.get("network", False),
        "timeOutput": caps.get("time_output", False),
        "adjustWeight": caps.get("adjust_weight", False),
        "animate": caps.get("animate", False),
    }


def _sensory_system_to_frontend(env: SensorySystem) -> dict:
    """Serialize SensorySystem for the frontend."""
    inputs = []
    for s in env.inputs:
        entry: dict = {"id": s.id, "label": s.label, "default": s.default}
        if s.is_spatial:
            entry["isSpatial"] = True
        if _is_toggleable(s):
            entry["uniform"] = "u_" + s.id
        if s._is_derived():
            entry["derived"] = True
        inputs.append(entry)

    outputs = [{"id": o.id, "label": o.label} for o in env.outputs]

    derived = []
    for d in env.derived_inputs:
        derived.append({"id": d.id, "deps": list(d.deps), "glsl": d.render_code})

    return {
        "inputs": inputs,
        "outputs": outputs,
        "derivedInputs": derived,
    }


def export_representations_for_frontend() -> list[dict]:
    """
    Return per-representation config for the frontend representation registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys,
    capabilities, sensorySystem, phenotype.
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
        rep_data["sensorySystem"] = _sensory_system_to_frontend(rep.sensory_system)
        rep_data["phenotype"] = _phenotype_to_frontend(rep.phenotype)
        result.append(rep_data)
    return result

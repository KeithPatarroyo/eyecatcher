"""
Export representation metadata for frontend code generation.

Used by scripts/generate_representation_config.py to emit
config.generated.js for the frontend.
Metadata is defined on each representation class (frontend_metadata); capabilities
are derived from the protocol (get_representation_capabilities).
"""

from __future__ import annotations

from .protocol import get_representation_capabilities
from .registry import REPRESENTATIONS, get_representation


def _capabilities_to_frontend(caps: dict[str, bool]) -> dict[str, bool]:
    """Convert snake_case capability keys to frontend camelCase."""
    return {
        "save": caps.get("save", False),
        "network": caps.get("network", False),
        "timeOutput": caps.get("time_output", False),
        "adjustWeight": caps.get("adjust_weight", False),
    }


def export_representations_for_frontend() -> list[dict]:
    """
    Return per-representation config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys, capabilities.
    Capabilities are derived from optional protocol methods
    (not stored in frontend_metadata).
    """
    result = []
    for rid in REPRESENTATIONS:
        rep = get_representation(rid)
        entry = getattr(rep.__class__, "frontend_metadata", None)
        if not isinstance(entry, dict):
            entry = {}
        caps = get_representation_capabilities(rep)
        result.append(
            {
                "id": rid,
                "outputType": getattr(rep.__class__, "output_type", "shader"),
                **entry,
                "capabilities": _capabilities_to_frontend(caps),
            }
        )
    return result

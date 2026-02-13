"""
Export substrate metadata for frontend code generation.

Used by scripts/generate_substrate_config.py to emit substrate_adapters.generated.js.
Frontend metadata lives here so substrate classes stay pure evolution logic.
"""

from __future__ import annotations

from .registry import SUBSTRATES

# Frontend metadata keyed by substrate id. Add new substrates here when registering.
SUBSTRATE_FRONTEND_METADATA: dict[str, dict] = {
    "dual_cppn": {
        "hasSignalControls": True,
        "genomeKeys": ["visual", "time_signal"],
        "capabilities": {
            "save": True,
            "network": True,
            "timeOutput": True,
            "adjustWeight": True,
        },
    },
    "single_cppn": {
        "hasSignalControls": False,
        "genomeKeys": ["visual"],
        "excludeKeys": ["time_signal"],
        "capabilities": {
            "save": True,
            "network": False,
            "timeOutput": False,
            "adjustWeight": False,
        },
    },
    "ca": {
        "hasSignalControls": False,
        "genomeKeys": ["rule"],
        "capabilities": {
            "save": True,
            "network": False,
            "timeOutput": False,
            "adjustWeight": False,
        },
    },
}


def export_substrates_for_frontend() -> list[dict]:
    """
    Return per-substrate config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys, capabilities.
    Optional excludeKeys. From SUBSTRATES and SUBSTRATE_FRONTEND_METADATA.
    """
    result = []
    for sid, cls in SUBSTRATES.items():
        entry = SUBSTRATE_FRONTEND_METADATA.get(sid, {})
        result.append(
            {
                "id": sid,
                "outputType": getattr(cls, "output_type", "shader"),
                **entry,
            }
        )
    return result

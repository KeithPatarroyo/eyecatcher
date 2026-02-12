"""
Export substrate metadata for frontend code generation.

Used by scripts/generate_substrate_config.py to emit substrate_adapters.generated.js.
Builds list from SUBSTRATES registry and each substrate's get_frontend_metadata().
"""

from __future__ import annotations

from .registry import SUBSTRATES


def export_substrates_for_frontend() -> list[dict]:
    """
    Return per-substrate config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys, capabilities.
    Optional excludeKeys. From SUBSTRATES and each class's get_frontend_metadata().
    """
    result = []
    for sid, cls in SUBSTRATES.items():
        meta = getattr(cls, "get_frontend_metadata", None)
        if callable(meta):
            entry = meta()
        else:
            entry = {}
        result.append(
            {
                "id": sid,
                "outputType": getattr(cls, "output_type", "shader"),
                **entry,
            }
        )
    return result

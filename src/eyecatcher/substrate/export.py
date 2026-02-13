"""
Export substrate metadata for frontend code generation.

Used by scripts/generate_substrate_config.py to emit substrate_adapters.generated.js.
Metadata is defined on each substrate class (frontend_metadata) so there is a single
source of truth; no separate dict to keep in sync.
"""

from __future__ import annotations

from .registry import SUBSTRATES


def export_substrates_for_frontend() -> list[dict]:
    """
    Return per-substrate config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys, capabilities.
    Optional excludeKeys. Built from SUBSTRATES; each substrate class should define
    a class attribute frontend_metadata with those keys.
    """
    result = []
    for sid, cls in SUBSTRATES.items():
        entry = getattr(cls, "frontend_metadata", None)
        if not isinstance(entry, dict):
            entry = {}
        result.append(
            {
                "id": sid,
                "outputType": getattr(cls, "output_type", "shader"),
                **entry,
            }
        )
    return result

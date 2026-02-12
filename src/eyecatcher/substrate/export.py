"""
Export substrate metadata for frontend code generation.

Used by scripts/generate_substrate_config.py to emit substrate_adapters.generated.js.
Keeps substrate ids, output_type, and genome-format rules in one place.
"""

from __future__ import annotations


def export_substrates_for_frontend() -> list[dict]:
    """
    Return per-substrate config for the frontend adapter registry.

    Each entry has: id, outputType, hasSignalControls, genomeKeys, capabilities.
    Optional excludeKeys for substrates that require a key absent
    (e.g. single_cppn: no time_signal). The JS registry builds
    isGenomeFormat from genomeKeys/excludeKeys.
    capabilities: { save, network, timeOutput, adjustWeight }
    """
    return [
        {
            "id": "dual_cppn",
            "outputType": "shader",
            "hasSignalControls": True,
            "genomeKeys": ["visual", "time_signal"],
            "capabilities": {
                "save": True,
                "network": True,
                "timeOutput": True,
                "adjustWeight": True,
            },
        },
        {
            "id": "single_cppn",
            "outputType": "shader",
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
        {
            "id": "ca",
            "outputType": "grid",
            "hasSignalControls": False,
            "genomeKeys": ["rule"],
            "capabilities": {
                "save": True,
                "network": False,
                "timeOutput": False,
                "adjustWeight": False,
            },
        },
    ]

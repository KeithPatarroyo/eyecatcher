"""
Substrate registry: factory for creating substrate instances from preset config.

Experiment presets in config/experiments.json can set "substrate": "dual_cppn" etc.;
get_substrate() builds the configured substrate from the preset.
"""

from __future__ import annotations

from typing import Any

from .ca import ElementaryCASubstrate
from .dual_cppn import DualCPPNSubstrate
from .protocol import Substrate

# Concrete substrate classes keyed by id; all implement Substrate protocol.
SUBSTRATES: dict[str, type] = {
    "dual_cppn": DualCPPNSubstrate,
    "ca": ElementaryCASubstrate,
}


def get_substrate(substrate_id: str | None = None, **kwargs: Any) -> Substrate[Any]:
    """
    Return a substrate instance.

    Args:
        substrate_id: Substrate key (e.g. "dual_cppn"). None => "dual_cppn".
        **kwargs: Passed to substrate constructor (e.g. neat_config_path).

    Returns:
        Configured substrate instance.

    Raises:
        KeyError: If substrate_id is not in SUBSTRATES.
    """
    sid = substrate_id or "dual_cppn"
    if sid not in SUBSTRATES:
        raise KeyError(f"Unknown substrate: {sid}. Known: {list(SUBSTRATES)}")
    return SUBSTRATES[sid](**kwargs)

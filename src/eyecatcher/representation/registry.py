"""
Representation registry: factory for representation instances from preset config.

Experiment presets in config/experiments.json can set
"representation": "nca" etc.; get_representation() builds the configured
representation from the preset.
"""

from __future__ import annotations

from typing import Any

from .ca import ConwayRepresentation
from .dual_cppn import DualCPPNRepresentation
from .nca import NCARepresentation
from .protocol import Representation
from .single_cppn import SingleCPPNRepresentation

# Default when no preset or representation_id is set (single source of truth).
DEFAULT_REPRESENTATION_ID = "nca"

# Concrete representation classes keyed by id; all implement Representation protocol.
REPRESENTATIONS: dict[str, type] = {
    "dual_cppn": DualCPPNRepresentation,
    "single_cppn": SingleCPPNRepresentation,
    "ca": ConwayRepresentation,
    "nca": NCARepresentation,
}


def get_representation(
    representation_id: str | None = None, **kwargs: Any
) -> Representation[Any]:
    """
    Return a representation instance.

    Args:
        representation_id: Representation key (e.g. "nca"). None => default.
        **kwargs: Passed to representation constructor (e.g. neat_config_path).

    Returns:
        Configured representation instance.

    Raises:
        KeyError: If representation_id is not in REPRESENTATIONS.
    """
    rid = representation_id or DEFAULT_REPRESENTATION_ID
    if rid not in REPRESENTATIONS:
        raise KeyError(f"Unknown representation: {rid}. Known: {list(REPRESENTATIONS)}")
    return REPRESENTATIONS[rid](**kwargs)

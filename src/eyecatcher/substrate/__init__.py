"""
Pluggable substrates: CPPN, NCA, CA, neural nets share a common protocol.

Use get_substrate(id, **preset_kwargs) to obtain the configured substrate;
evolution and API use the substrate interface only.
"""

from .ca import CARule, ElementaryCASubstrate
from .dual_cppn import DualCPPNSubstrate
from .protocol import OutputType, Substrate, SubstrateOutput
from .registry import SUBSTRATES, get_substrate

__all__ = [
    "CARule",
    "DualCPPNSubstrate",
    "ElementaryCASubstrate",
    "OutputType",
    "Substrate",
    "SubstrateOutput",
    "SUBSTRATES",
    "get_substrate",
]

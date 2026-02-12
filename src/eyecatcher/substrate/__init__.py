"""
Pluggable substrates: CPPN, NCA, CA, neural nets share a common protocol.

Use get_substrate(id, **preset_kwargs) to obtain the configured substrate;
evolution and API use the substrate interface only.
"""

from .ca import CARule, ElementaryCASubstrate
from .dual_cppn import DualCPPNSubstrate
from .export import export_substrates_for_frontend
from .protocol import OutputType, Substrate, SubstrateOutput
from .registry import SUBSTRATES, get_substrate
from .single_cppn import SingleCPPNSubstrate

__all__ = [
    "export_substrates_for_frontend",
    "CARule",
    "DualCPPNSubstrate",
    "ElementaryCASubstrate",
    "OutputType",
    "Substrate",
    "SubstrateOutput",
    "SUBSTRATES",
    "SingleCPPNSubstrate",
    "get_substrate",
]

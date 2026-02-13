"""
Pluggable substrates: CPPN, NCA, CA, neural nets share a common protocol.

Use get_substrate(id, **preset_kwargs) to obtain the configured substrate;
evolution and API use the substrate interface only.
Dual-genome type and helpers (DualGenome, create_random_dual_genome, etc.) are here.
"""

from .ca import CARule, ElementaryCASubstrate
from .dual_cppn import DualCPPNSubstrate
from .dual_genome import (
    DualGenome,
    copy_dual_genome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from .export import export_substrates_for_frontend
from .protocol import OutputType, Substrate, SubstrateOutput
from .registry import SUBSTRATES, get_substrate
from .single_cppn import SingleCPPNSubstrate

__all__ = [
    "CARule",
    "DualCPPNSubstrate",
    "DualGenome",
    "ElementaryCASubstrate",
    "OutputType",
    "Substrate",
    "SubstrateOutput",
    "SUBSTRATES",
    "SingleCPPNSubstrate",
    "copy_dual_genome",
    "create_random_dual_genome",
    "dual_genome_from_json",
    "dual_genome_to_json",
    "export_substrates_for_frontend",
    "get_substrate",
]

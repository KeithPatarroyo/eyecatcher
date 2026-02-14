"""
Pluggable representations: CPPN, NCA, CA, neural nets share a common protocol.

Use get_representation(id, **preset_kwargs) to obtain the configured representation;
evolution and API use the representation interface only.
"""

from .ca import ConwayGenome, ConwayRepresentation
from .dual_cppn import DualCPPNRepresentation
from .export import export_representations_for_frontend
from .protocol import OutputType, Representation, RepresentationOutput
from .registry import REPRESENTATIONS, get_representation
from .single_cppn import SingleCPPNRepresentation

__all__ = [
    "ConwayGenome",
    "ConwayRepresentation",
    "DualCPPNRepresentation",
    "OutputType",
    "Representation",
    "RepresentationOutput",
    "REPRESENTATIONS",
    "SingleCPPNRepresentation",
    "export_representations_for_frontend",
    "get_representation",
]

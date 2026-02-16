"""
Pluggable representations: CPPN, NCA, CA, neural nets share a common protocol.

Use get_representation(id, **preset_kwargs) to obtain the configured representation;
evolution and API use the representation interface only.
"""

from .ca import ConwayGenome, ConwayRepresentation
from .dual_cppn import DualCPPNRepresentation
from .export import export_representations_for_frontend
from .mixins import (
    GridAnalyzable,
    NetworkInspectable,
    Samplable,
    Saveable,
)
from .protocol import OutputType, Phenotype, Representation, RepresentationOutput
from .registry import REPRESENTATIONS, get_representation
from .single_cppn import SingleCPPNRepresentation

__all__ = [
    "ConwayGenome",
    "ConwayRepresentation",
    "DualCPPNRepresentation",
    "GridAnalyzable",
    "NetworkInspectable",
    "OutputType",
    "Phenotype",
    "Representation",
    "RepresentationOutput",
    "REPRESENTATIONS",
    "Samplable",
    "Saveable",
    "SingleCPPNRepresentation",
    "export_representations_for_frontend",
    "get_representation",
]

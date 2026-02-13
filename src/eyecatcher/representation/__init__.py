"""
Pluggable representations: CPPN, NCA, CA, neural nets share a common protocol.

Use get_representation(id, **preset_kwargs) to obtain the configured representation;
evolution and API use the representation interface only.
Dual-genome type and helpers (DualGenome, create_random_dual_genome, etc.) are here.
"""

from ..genome.dual import (
    DualGenome,
    copy_dual_genome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from .ca import ConwayGenome, ConwayRepresentation
from .dual_cppn import DualCPPNRepresentation
from .export import export_representations_for_frontend
from .protocol import OutputType, Representation, RepresentationOutput
from .registry import REPRESENTATIONS, get_representation
from .single_cppn import SingleCPPNRepresentation
from .sockets import GridSocket, NeatSocket

__all__ = [
    "ConwayGenome",
    "ConwayRepresentation",
    "DualCPPNRepresentation",
    "DualGenome",
    "GridSocket",
    "NeatSocket",
    "OutputType",
    "Representation",
    "RepresentationOutput",
    "REPRESENTATIONS",
    "SingleCPPNRepresentation",
    "copy_dual_genome",
    "create_random_dual_genome",
    "dual_genome_from_json",
    "dual_genome_to_json",
    "export_representations_for_frontend",
    "get_representation",
]

"""
Inspection: look inside genomes.

Network graph data for UI/API, genome visualization (PDF), graph algorithms.
CPU rendering and query live in substrate (cppn_base, dual_cppn, single_cppn).
"""

from .genome_visualizer import render_genome_network_pdf
from .network_data import extract_network_data, parse_network_node_id

__all__ = [
    "render_genome_network_pdf",
    "extract_network_data",
    "parse_network_node_id",
]

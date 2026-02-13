"""
Evaluation and output generation.

Fitness, visualization, and network graph/stats for UI/API.
CPU rendering and query live in substrate (cppn_base, dual_cppn, single_cppn).
"""

from .fitness import (
    FITNESS_REGISTRY,
    get_fitness,
    list_fitness,
    register_fitness,
)
from .genome_visualizer import render_genome_network_pdf
from .network_data import extract_network_data, parse_network_node_id

__all__ = [
    "FITNESS_REGISTRY",
    "get_fitness",
    "list_fitness",
    "register_fitness",
    "render_genome_network_pdf",
    "extract_network_data",
    "parse_network_node_id",
]

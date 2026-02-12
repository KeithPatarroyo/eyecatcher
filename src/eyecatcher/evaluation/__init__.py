"""
Evaluation and output generation.

Query (evaluation), rendering (CPU), visualization, and network graph/stats for UI/API.
"""

from .fitness import (
    FITNESS_REGISTRY,
    get_fitness,
    list_fitness,
    register_fitness,
)
from .genome_visualizer import render_genome_network_pdf
from .network_data import extract_network_data, parse_network_node_id
from .query import query_time_signal, query_visual_cppn
from .rendering import render_animation_frames, render_image

__all__ = [
    "FITNESS_REGISTRY",
    "get_fitness",
    "list_fitness",
    "register_fitness",
    "query_time_signal",
    "query_visual_cppn",
    "render_image",
    "render_animation_frames",
    "render_genome_network_pdf",
    "extract_network_data",
    "parse_network_node_id",
]

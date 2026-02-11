"""
Evaluation and output generation.

Query (evaluation), rendering (CPU), visualization, and network graph/stats for UI/API.
"""

from .genome_visualizer import render_genome_network_pdf
from .network_data import (
    dual_genome_network_stats,
    extract_network_data,
    parse_network_node_id,
)
from .query import query_dual_cppn, query_time_signal, query_visual_cppn
from .rendering import (
    render_animation_frames,
    render_dual_animation_frames,
    render_dual_image,
    render_image,
)

__all__ = [
    "query_time_signal",
    "query_visual_cppn",
    "query_dual_cppn",
    "render_image",
    "render_animation_frames",
    "render_dual_image",
    "render_dual_animation_frames",
    "render_genome_network_pdf",
    "dual_genome_network_stats",
    "extract_network_data",
    "parse_network_node_id",
]

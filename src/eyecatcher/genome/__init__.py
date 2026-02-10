"""
Genome representation and serialization.

DualGenome, genome creation, and JSON serialization/deserialization.
"""

from .genome import DualGenome, create_random_dual_genome, create_random_genome
from .serialization import (
    copy_dual_genome,
    copy_genome,
    dual_genome_from_json,
    dual_genome_network_stats,
    dual_genome_to_json,
    extract_network_data,
    genome_from_json,
    genome_to_json,
    parse_network_node_id,
)

__all__ = [
    "DualGenome",
    "create_random_genome",
    "create_random_dual_genome",
    "genome_to_json",
    "genome_from_json",
    "dual_genome_to_json",
    "dual_genome_from_json",
    "copy_genome",
    "copy_dual_genome",
    "dual_genome_network_stats",
    "extract_network_data",
    "parse_network_node_id",
]

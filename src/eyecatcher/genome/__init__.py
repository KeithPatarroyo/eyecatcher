"""
Genome representation and serialization.

DualGenome, genome creation, JSON serialization.
Network graph (extract_network_data, parse_network_node_id) live in
evaluation.network_data; import from eyecatcher.evaluation or evaluation.network_data.
"""

from .genome import DualGenome, create_random_dual_genome, create_random_genome
from .serialization import (
    copy_dual_genome,
    copy_genome,
    dual_genome_from_json,
    dual_genome_to_json,
    genome_from_json,
    genome_to_json,
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
]

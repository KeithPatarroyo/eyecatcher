"""
Genome representation and serialization.

Generic NEAT genome: create_random_genome, genome_to_json, genome_from_json,
copy_genome. Dual-genome types and helpers live in substrate._dual_genome and
are exported from substrate.
"""

from .genome import create_random_genome
from .serialization import copy_genome, genome_from_json, genome_to_json

__all__ = [
    "create_random_genome",
    "copy_genome",
    "genome_from_json",
    "genome_to_json",
]

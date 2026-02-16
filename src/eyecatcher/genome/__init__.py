"""
Genome representation and serialization.

Generic NEAT genome: create_random_genome, genome_to_json, genome_from_json,
copy_genome. Dual-genome type and helpers live in genome.dual.
"""

from .dual import (
    DualGenome,
    copy_dual_genome,
    create_random_dual_genome,
    crossover_dual_genomes,
    dual_genome_from_json,
    dual_genome_to_json,
    mutate_dual_genome,
)
from .operators import create_random_genome
from .serialization import copy_genome, genome_from_json, genome_to_json

__all__ = [
    "copy_dual_genome",
    "copy_genome",
    "create_random_dual_genome",
    "create_random_genome",
    "crossover_dual_genomes",
    "dual_genome_from_json",
    "dual_genome_to_json",
    "DualGenome",
    "genome_from_json",
    "genome_to_json",
    "mutate_dual_genome",
]

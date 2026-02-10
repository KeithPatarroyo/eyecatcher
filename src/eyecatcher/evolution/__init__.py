"""
Evolution subpackage: dual-CPPN engine, genomes, operators, serialization, rendering.

This is the preferred import surface for evolution; use
``from eyecatcher.evolution import ...``.

Public API for researchers and the rest of the app:
- CPPNEngine, DualGenome, ShaderCompiler
- create_random_genome, create_random_dual_genome
- Serialization: genome_to_json, genome_from_json, dual_genome_to_json,
  dual_genome_from_json, copy_genome, copy_dual_genome, dual_genome_network_stats,
  extract_network_data, parse_network_node_id
- Config constants (e.g. NEAT_CONFIG_PATH, DEFAULT_POPULATION_SIZE) via evolution.config
"""

from . import serialization
from .config import (
    DEFAULT_NUM_FRAMES,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_TIME,
    MAX_POPULATION_SIZE,
    MUTATION_PROBABILITY,
    NEAT_CONFIG_PATH,
    NEAT_TIME_CONFIG_PATH,
    PREVIEW_RENDER_RESOLUTION,
)
from .engine import CPPNEngine
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
from .shader_compiler import ShaderCompiler

__all__ = [
    "CPPNEngine",
    "DualGenome",
    "ShaderCompiler",
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
    "serialization",
    "NEAT_CONFIG_PATH",
    "NEAT_TIME_CONFIG_PATH",
    "DEFAULT_POPULATION_SIZE",
    "MUTATION_PROBABILITY",
    "MAX_POPULATION_SIZE",
    "DEFAULT_RENDER_RESOLUTION",
    "DEFAULT_RENDER_TIME",
    "PREVIEW_RENDER_RESOLUTION",
    "DEFAULT_NUM_FRAMES",
]

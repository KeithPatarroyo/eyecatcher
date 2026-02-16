"""
Dual-genome type and operations: visual + time_signal NEAT genomes.

Used by DualCPPNRepresentation. Generic NEAT genome types live in this package.
"""

from __future__ import annotations

from typing import Any

import neat

from .operators import create_random_genome
from .serialization import (
    _update_node_indexer_from_genome,
    genome_from_json,
    genome_to_json,
)


class DualGenome:
    """
    A paired genome consisting of a visual CPPN and a time signal CPPN.
    Both are evolved together with shared fitness.
    """

    __slots__ = ("visual", "time_signal", "key")

    def __init__(
        self,
        visual: neat.DefaultGenome,
        time_signal: neat.DefaultGenome,
        key: int = 0,
    ):
        self.visual = visual
        self.time_signal = time_signal
        self.key = key

    @property
    def fitness(self):
        """Return fitness (stored on visual genome)."""
        return self.visual.fitness

    @fitness.setter
    def fitness(self, value):
        """Set fitness on both genomes."""
        self.visual.fitness = value
        self.time_signal.fitness = value


def create_random_dual_genome(
    visual_config: neat.Config,
    time_config: neat.Config,
    genome_id: int = 0,
    key: int | None = None,
) -> DualGenome:
    """Create a random dual genome (visual + time signal CPPNs)."""
    k = key if key is not None else genome_id
    visual_genome = create_random_genome(visual_config, genome_id=k, key=k)
    time_genome = create_random_genome(time_config, genome_id=k, key=k)
    return DualGenome(visual=visual_genome, time_signal=time_genome, key=k)


def dual_genome_to_json(dual: DualGenome) -> dict[str, Any]:
    """Serialize a DualGenome to a JSON-serializable dict."""
    return {
        "key": dual.key,
        "visual": genome_to_json(dual.visual),
        "time_signal": genome_to_json(dual.time_signal),
    }


def dual_genome_from_json(
    data: dict[str, Any],
    visual_config: neat.Config,
    time_config: neat.Config,
) -> DualGenome:
    """Deserialize a DualGenome from a dict (e.g. from JSON)."""
    visual_data = data.get("visual", {})
    time_data = data.get("time_signal", {})
    if not visual_data or not time_data:
        raise ValueError("dual genome JSON must contain 'visual' and 'time_signal'")

    visual = genome_from_json(visual_data, visual_config)
    time_signal = genome_from_json(time_data, time_config)
    _update_node_indexer_from_genome(visual, visual_config.genome_config)
    _update_node_indexer_from_genome(time_signal, time_config.genome_config)

    key = data.get("key", 0)
    return DualGenome(visual=visual, time_signal=time_signal, key=key)


def copy_dual_genome(
    dual: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: int | None = None,
) -> DualGenome:
    """Create a deep copy of a dual genome."""
    from .serialization import copy_genome

    return DualGenome(
        visual=copy_genome(dual.visual, visual_config),
        time_signal=copy_genome(dual.time_signal, time_config),
        key=new_key if new_key is not None else dual.key,
    )


def mutate_dual_genome(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: int,
) -> DualGenome:
    """Create a mutated copy of a dual genome (both visual and time signal)."""
    from .operators import mutate_genome

    visual_child = mutate_genome(dual_genome.visual, visual_config, key=new_key)
    time_child = mutate_genome(dual_genome.time_signal, time_config, key=new_key)
    return DualGenome(visual=visual_child, time_signal=time_child, key=new_key)


def crossover_dual_genomes(
    dual1: DualGenome,
    dual2: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: int,
) -> DualGenome:
    """Create offspring from two dual genomes."""
    from .operators import crossover_genomes

    visual_child = crossover_genomes(
        dual1.visual, dual2.visual, visual_config, key=new_key
    )
    time_child = crossover_genomes(
        dual1.time_signal, dual2.time_signal, time_config, key=new_key
    )
    return DualGenome(visual=visual_child, time_signal=time_child, key=new_key)

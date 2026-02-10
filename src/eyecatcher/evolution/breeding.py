"""
Stateless breeding: produce next generation from parent genome payloads.

Used by the server /api/breed endpoint. Callers pass an engine and parent
data; this module returns children as list of genome JSON dicts. Researchers
can change selection/elitism here.
"""

import logging
import random
from typing import TYPE_CHECKING, Any, Optional

from . import config as evolution_config
from . import serialization

if TYPE_CHECKING:
    from .engine import CPPNEngine

logger = logging.getLogger(__name__)


def breed_next_generation(
    engine: "CPPNEngine",
    parents_data: list[dict[str, Any]],
    population_size: Optional[int] = None,
    elitism: bool = False,
    mutation_probability: Optional[float] = None,
) -> list:
    """
    Produce children from parent payloads (stateless).

    Args:
        engine: CPPNEngine instance for mutation/crossover and deserialization.
        parents_data: List of dicts with "genome" (or self) and
            optional "clicks" (fitness).
        population_size: Number of children to produce. Default from config.
        elitism: If True, best parent is copied as first child.
        mutation_probability: Probability of mutation vs crossover. Default from config.

    Returns:
        List of dual-genome JSON dicts (dual_genome_to_json per child).
    """
    if population_size is None:
        population_size = evolution_config.DEFAULT_POPULATION_SIZE
    if mutation_probability is None:
        mutation_probability = evolution_config.MUTATION_PROBABILITY

    parents = []
    for idx, p in enumerate(parents_data):
        try:
            genome_data = p.get("genome", p)
            dual = serialization.dual_genome_from_json(
                genome_data, engine.config, engine.time_config
            )
            dual.fitness = p.get("clicks", 0)
            parents.append({"genome": dual, "clicks": p.get("clicks", 0)})
        except Exception as e:
            logger.warning("Failed to parse parent %s: %s. Parent data: %s", idx, e, p)
            continue

    if not parents:
        raise ValueError("No valid parents")

    max_key = max(p["genome"].key for p in parents)
    next_key = max_key + 1
    children = []

    if elitism:
        best = max(parents, key=lambda x: x["clicks"])
        elite = serialization.copy_dual_genome(
            best["genome"], engine.config, engine.time_config, next_key
        )
        children.append(serialization.dual_genome_to_json(elite))
        next_key += 1

    while len(children) < population_size:
        if len(parents) == 1:
            child = engine.mutate_dual_genome(parents[0]["genome"], next_key)
        else:
            if random.random() < mutation_probability:
                parent = random.choice(parents)
                child = engine.mutate_dual_genome(parent["genome"], next_key)
            else:
                p1, p2 = random.sample(parents, 2)
                child = engine.crossover_dual_genomes(
                    p1["genome"], p2["genome"], next_key
                )
        children.append(serialization.dual_genome_to_json(child))
        next_key += 1

    return children

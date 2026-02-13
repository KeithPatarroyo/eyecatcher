"""
Stateless reproduction: produce next generation from parent genome payloads.

Selection, crossover, and mutation. Used by the server /api/evolve endpoint.
Callers pass a substrate; this module returns children as list of genome JSON
dicts. Works with any substrate (dual_cppn, ca, etc.).
"""

import logging
import random
from typing import Any, Optional

from . import config as evolution_config

logger = logging.getLogger(__name__)


def produce_next_generation(
    substrate: Any,
    parents_data: list[dict[str, Any]],
    population_size: Optional[int] = None,
    elitism: bool = False,
    crossover_probability: Optional[float] = None,
) -> list:
    """
    Produce next generation from parent payloads (stateless).

    Uses selection (from parents_data), optional elitism, and crossover or
    mutation per child. Substrate-agnostic.

    Args:
        substrate: Substrate (create_random, mutate, crossover, from_json, to_json).
        parents_data: List of dicts with "genome" (or self) and optional "fitness".
        population_size: Number of children to produce. Default from config.
        elitism: If True, best parent is copied as first child (new key).
        crossover_probability: Crossover (two parents) vs mutate one parent.

    Returns:
        List of genome JSON dicts (substrate.to_json per child).
    """
    if population_size is None:
        population_size = evolution_config.DEFAULT_POPULATION_SIZE
    if crossover_probability is None:
        crossover_probability = evolution_config.CROSSOVER_PROBABILITY

    parents = []
    for idx, p in enumerate(parents_data):
        try:
            genome_data = p.get("genome", p)
            ind = substrate.from_json(genome_data)
            parents.append({"genome": ind, "fitness": p.get("fitness", 0)})
        except Exception as e:
            logger.warning("Failed to parse parent %s: %s. Parent data: %s", idx, e, p)
            continue

    if not parents:
        raise ValueError("No valid parents")

    max_key = max(getattr(p["genome"], "key", 0) for p in parents)
    next_key = max_key + 1
    children = []

    if elitism:
        best = max(parents, key=lambda x: x["fitness"])
        elite_json = {**substrate.to_json(best["genome"]), "key": next_key}
        elite = substrate.from_json(elite_json)
        children.append(substrate.to_json(elite))
        next_key += 1

    while len(children) < population_size:
        if len(parents) == 1:
            child = substrate.mutate(parents[0]["genome"], next_key)
        else:
            if random.random() < crossover_probability:
                p1, p2 = random.sample(parents, 2)
                child = substrate.crossover(p1["genome"], p2["genome"], next_key)
            else:
                parent = random.choice(parents)
                child = substrate.mutate(parent["genome"], next_key)
        children.append(substrate.to_json(child))
        next_key += 1

    return children

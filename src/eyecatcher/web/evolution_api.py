"""
Evolution API: /api/evolve and genealogy integration.

Produces next generation (stateless) and optionally saves to genealogy DB.
"""

import logging

from flask import Blueprint, jsonify, request

from .. import experiment
from ..evolution.reproduction import produce_next_generation
from .api_helpers import ERR_PARENTS_ARRAY_REQUIRED, api_error, api_try_except
from .stateless_api import get_current_representation

logger = logging.getLogger(__name__)

evolve_bp = Blueprint("evolve", __name__)


def _save_generation_to_genealogy(
    parent_population_id: int,
    generation_num: int,
    branch_name: str,
    children: list,
    metadata: dict | None = None,
) -> int | None:
    """Save children to genealogy DB; return new population id or None on failure."""
    try:
        from ..data import save_generation_result

        return save_generation_result(
            parent_population_id,
            generation_num,
            branch_name,
            children,
            metadata=metadata,
        )
    except Exception as e:
        logger.exception("Failed to save to genealogy: %s", e)
        return None


@evolve_bp.route("/api/evolve", methods=["POST"])
@api_try_except
def evolve():
    """
    Produce next generation (stateless). Selection, crossover, mutation.
    Body: {
        "parents": [ { "individual": {...}, "fitness"?: N } ],
        "population_size": 12,  (optional, default from config)
        "elitism": false  (optional; if true, best parent is copied unchanged)
    }
    Returns { "children": [individual JSONs] }.
    """
    data = request.json or {}
    if "parents" not in data:
        return api_error(ERR_PARENTS_ARRAY_REQUIRED, 400)
    parents_data = data.get("parents", [])
    if not parents_data:
        return api_error(ERR_PARENTS_ARRAY_REQUIRED, 400)

    population_size = data.get("population_size", experiment.get_population_size())
    crossover_probability = data.get(
        "crossover_probability", experiment.get_crossover_probability()
    )
    elitism = data.get("elitism", experiment.get_elitism_default())
    parent_population_id = data.get("parent_population_id")
    generation_num = data.get("generation_num", 0)
    branch_name = data.get("branch_name", "main")

    representation = get_current_representation()
    parents_for_evolution = [
        {
            "genome": p.get("individual", p.get("genome", p)),
            "fitness": p.get("fitness", 0),
        }
        for p in parents_data
    ]
    children = produce_next_generation(
        representation,
        parents_for_evolution,
        population_size=population_size,
        elitism=elitism,
        crossover_probability=crossover_probability,
    )

    new_pop_id = None
    if parent_population_id is not None:
        experiment_metadata = {
            "experiment_config": {
                "representation_id": representation.id,
                "population_size": population_size,
                "crossover_probability": crossover_probability,
            }
        }
        new_pop_id = _save_generation_to_genealogy(
            parent_population_id,
            generation_num,
            branch_name,
            children,
            metadata=experiment_metadata,
        )

    payload = {
        "children": children,
        "output_type": representation.output_type,
        "representation_id": representation.id,
    }
    if new_pop_id is not None:
        payload["population_id"] = new_pop_id
    return jsonify(payload)

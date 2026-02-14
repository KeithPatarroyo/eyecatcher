"""
Genealogy API Blueprint for Eyecatcher.

Tracks evolutionary history: populations, individuals, and their relationships.
Auto-saves every generation to enable branch exploration and time-travel evolution.
Data layer: genealogy_db.py. Routes are thin: parse request, call db, jsonify.
"""

from flask import Blueprint, Response, jsonify, request

from ..data.genealogy_db import (
    export_genealogy_data,
    export_sizes,
    get_branches,
    get_experiment_log,
    get_population,
    get_population_thumbnail,
    get_stats,
    get_tree_nodes,
    init_genealogy_db,
    reset_genealogy,
    save_population,
)
from ..experiment import (
    get_configured_representation,
    get_crossover_probability,
    get_population_size,
)
from .api_helpers import ERR_INDIVIDUALS_ARRAY_REQUIRED, api_error, api_try_except

# Create blueprint
genealogy_bp = Blueprint("genealogy", __name__)

# Initialize DB on module load
init_genealogy_db()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@genealogy_bp.route("/api/genealogy/save-population", methods=["POST"])
@api_try_except
def save_population_route():
    """POST save-population: body individuals, parent_id, gen_num, branch; returns ids."""  # noqa: E501
    data = request.json or {}
    individuals = data.get("individuals", [])
    parent_id = data.get("parent_id")
    generation_num = data.get("generation_num", 0)
    branch_name = data.get("branch_name", "main")
    description = data.get("description", "")
    user_id = data.get("user_id", "anonymous")
    fitness_data = data.get("fitness_data", [])
    metadata = data.get("metadata") or {}
    if data.get("representation_id") is not None:
        metadata = dict(metadata, representation_id=data.get("representation_id"))
    representation = get_configured_representation()
    metadata = dict(
        metadata,
        experiment_config={
            "representation_id": representation.id,
            "population_size": get_population_size(),
            "crossover_probability": get_crossover_probability(),
        },
    )

    if not individuals:
        return api_error(ERR_INDIVIDUALS_ARRAY_REQUIRED, 400)

    result = save_population(
        genomes=individuals,
        parent_id=parent_id,
        generation_num=generation_num,
        branch_name=branch_name,
        description=description,
        user_id=user_id,
        fitness_data=fitness_data,
        metadata=metadata if metadata else None,
    )
    if "error" in result:
        if result["error"] == "parent_not_found":
            return api_error("parent_id not found", 400)
        return (
            jsonify(
                {
                    "error": "generation_num must be parent generation_num + 1",
                    "parent_generation_num": result["parent_generation_num"],
                }
            ),
            400,
        )
    return jsonify(result)


@genealogy_bp.route("/api/experiment-log", methods=["GET"])
@api_try_except
def experiment_log_route():
    """
    GET experiment-log: recent population save events with metadata (for research).
    Query: ?limit=200 (default), ?format=csv for CSV export.
    """
    limit = request.args.get("limit", "200", type=str)
    try:
        limit = min(1000, max(1, int(limit)))
    except (TypeError, ValueError):
        limit = 200
    fmt = (request.args.get("format") or "").strip().lower()
    log = get_experiment_log(limit=limit)
    if fmt == "csv":
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "id",
                "created_at",
                "branch_name",
                "generation_num",
                "population_size",
                "representation_id",
                "crossover_probability",
            ]
        )
        for row in log:
            exp = (row.get("metadata") or {}).get("experiment_config") or {}
            writer.writerow(
                [
                    row.get("id"),
                    row.get("created_at"),
                    row.get("branch_name"),
                    row.get("generation_num"),
                    row.get("population_size"),
                    exp.get("representation_id", exp.get("substrate_id", "")),
                    exp.get("crossover_probability", ""),
                ]
            )
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=experiment-log.csv"},
        )
    return jsonify({"entries": log})


@genealogy_bp.route(
    "/api/genealogy/load-population/<int:population_id>", methods=["GET"]
)
@api_try_except
def load_population(population_id):
    """GET load-population/<id>: returns population metadata and individuals list."""
    result = get_population(population_id)
    if result is None:
        return api_error("Population not found", 404)
    payload = {k: v for k, v in result.items() if k != "genomes"}
    payload["individuals"] = result.get("genomes", [])
    return jsonify(payload)


@genealogy_bp.route("/api/genealogy/tree", methods=["GET"])
@api_try_except
def get_tree():
    """GET tree: nodes (all populations: id, parent_id, generation_num, etc.)."""
    nodes = get_tree_nodes()
    return jsonify({"nodes": nodes})


@genealogy_bp.route("/api/genealogy/branches", methods=["GET"])
@api_try_except
def get_branches_route():
    """GET branches: names with latest_generation, latest_population_id, node_count."""
    branches = get_branches()
    return jsonify({"branches": branches})


@genealogy_bp.route("/api/genealogy/reset", methods=["POST"])
@api_try_except
def reset_genealogy_route():
    """POST reset: clear all genealogy data; returns { status: ok }."""
    reset_genealogy()
    return jsonify({"status": "ok"})


@genealogy_bp.route("/api/genealogy/export-sizes", methods=["GET"])
@api_try_except
def export_sizes_route():
    """GET export-sizes: full and per-branch estimated export sizes (download modal)."""
    result = export_sizes()
    return jsonify(result)


@genealogy_bp.route("/api/genealogy/export", methods=["GET"])
@api_try_except
def export_genealogy_route():
    """GET export: ?branch_name= optional; JSON (populations + individuals)."""
    branch_name = request.args.get("branch_name", "").strip() or None
    result = export_genealogy_data(branch_name)
    if result is None and branch_name:
        return (
            jsonify({"error": "Branch not found or empty", "branch_name": branch_name}),
            404,
        )
    return jsonify(result)


@genealogy_bp.route("/api/genealogy/stats", methods=["GET"])
@api_try_except
def get_stats_route():
    """GET stats: total_populations, total_individuals, total_branches, max_gen."""
    result = get_stats()
    return jsonify(result)


@genealogy_bp.route(
    "/api/genealogy/population-thumbnail/<int:population_id>", methods=["GET"]
)
@api_try_except
def get_population_thumbnail_route(population_id):
    """GET population-thumbnail/<id>: fittest individual and fitness for thumbnail."""
    result = get_population_thumbnail(population_id)
    if result is None:
        return (
            jsonify({"error": "No individuals found in this population"}),
            404,
        )
    payload = {"individual": result["genome"], "fitness": result["fitness"]}
    return jsonify(payload)

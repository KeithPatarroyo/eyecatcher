"""
Genealogy API Blueprint for Eyecatcher.

Tracks evolutionary history: populations, individuals, and their relationships.
Auto-saves every generation to enable branch exploration and time-travel evolution.
Data layer: genealogy_db.py. Routes are thin: parse request, call db, jsonify.
"""

from flask import Blueprint, jsonify, request

from ..data.genealogy_db import (
    export_genealogy_data,
    export_sizes,
    get_branches,
    get_population,
    get_population_thumbnail,
    get_stats,
    get_tree_nodes,
    init_genealogy_db,
    reset_genealogy,
    save_population,
)
from .api_helpers import ERR_GENOMES_ARRAY_REQUIRED, api_error

# Create blueprint
genealogy_bp = Blueprint("genealogy", __name__)

# Initialize DB on module load
init_genealogy_db()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@genealogy_bp.route("/api/genealogy/save-population", methods=["POST"])
def save_population_route():
    """POST save-population: body genomes, parent_id, gen_num, branch; returns ids."""
    try:
        data = request.json or {}
        genomes = data.get("genomes", [])
        parent_id = data.get("parent_id")
        generation_num = data.get("generation_num", 0)
        branch_name = data.get("branch_name", "main")
        description = data.get("description", "")
        user_id = data.get("user_id", "anonymous")
        fitness_data = data.get("fitness_data", [])
        metadata = data.get("metadata") or {}
        if data.get("substrate_id") is not None:
            metadata = dict(metadata, substrate_id=data.get("substrate_id"))

        if not genomes:
            return api_error(ERR_GENOMES_ARRAY_REQUIRED, 400)

        result = save_population(
            genomes=genomes,
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
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route(
    "/api/genealogy/load-population/<int:population_id>", methods=["GET"]
)
def load_population(population_id):
    """GET load-population/<id>: returns population metadata and genomes list."""
    try:
        result = get_population(population_id)
        if result is None:
            return api_error("Population not found", 404)
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/tree", methods=["GET"])
def get_tree():
    """GET tree: nodes (all populations: id, parent_id, generation_num, etc.)."""
    try:
        nodes = get_tree_nodes()
        return jsonify({"nodes": nodes})
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/branches", methods=["GET"])
def get_branches_route():
    """GET branches: names with latest_generation, latest_population_id, node_count."""
    try:
        branches = get_branches()
        return jsonify({"branches": branches})
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/reset", methods=["POST"])
def reset_genealogy_route():
    """POST reset: clear all genealogy data; returns { status: ok }."""
    try:
        reset_genealogy()
        return jsonify({"status": "ok"})
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/export-sizes", methods=["GET"])
def export_sizes_route():
    """GET export-sizes: full and per-branch estimated export sizes (download modal)."""
    try:
        result = export_sizes()
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/export", methods=["GET"])
def export_genealogy_route():
    """GET export: ?branch_name= optional; JSON (populations + individuals)."""
    branch_name = request.args.get("branch_name", "").strip() or None
    try:
        result = export_genealogy_data(branch_name)
        if result is None and branch_name:
            return (
                jsonify(
                    {"error": "Branch not found or empty", "branch_name": branch_name}
                ),
                404,
            )
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route("/api/genealogy/stats", methods=["GET"])
def get_stats_route():
    """GET stats: total_populations, total_individuals, total_branches, max_gen."""
    try:
        result = get_stats()
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), 500)


@genealogy_bp.route(
    "/api/genealogy/population-thumbnail/<int:population_id>", methods=["GET"]
)
def get_population_thumbnail_route(population_id):
    """GET population-thumbnail/<id>: fittest genome and fitness for thumbnail."""
    try:
        result = get_population_thumbnail(population_id)
        if result is None:
            return (
                jsonify({"error": "No individuals found in this population"}),
                404,
            )
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), 500)

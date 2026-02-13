"""
Interactive Evolution Server.

Serves population and handles evolution (stateless API). Population state lives
on the client; server provides compile, random, evolve, save. Save returns file
contents for client-side download (Railway / no server filesystem). Substrate
(dual_cppn, single_cppn, ca, etc.) is configured via experiments.json.
"""

import base64
import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .. import get_root_dir
from ..evolution import config
from ..evolution.reproduction import produce_next_generation
from .api_helpers import (
    ERR_GENOME_REQUIRED_REQUEST_BODY,
    ERR_PARENTS_ARRAY_REQUIRED,
    api_error,
    api_try_except,
    build_save_zip_response,
    numpy_to_png_base64,
)
from .community_routes import community_bp
from .genealogy_routes import genealogy_bp
from .stateless_api import get_current_substrate, init_stateless_api, stateless_bp

_log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT_DIR = get_root_dir()
STATIC_DIR = os.path.join(ROOT_DIR, "static")
# Default port when running locally; frontend dev port in evolution_config.js.
DEFAULT_PORT = 5001
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# CORS: allow all in dev, or set CORS_ORIGINS env for production
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
if _cors_origins == "*":
    CORS(app)
else:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(",")])

# Substrate from experiment preset (config/experiments.json, EXPERIMENT_CONFIG)
substrate = config.get_configured_substrate()
config.warn_if_neat_pop_size_mismatch(substrate)

# Initialize and register API blueprints
init_stateless_api(substrate)
app.register_blueprint(stateless_bp)
app.register_blueprint(community_bp)
app.register_blueprint(genealogy_bp)


@app.route("/health")
def health():
    """Lightweight health check for Railway/deploy (no app state)."""
    return "", 200


@app.route("/")
def index():
    """Serve the viewer HTML."""
    return send_from_directory(STATIC_DIR, "interactive_viewer.html")


@app.route("/genealogy")
def genealogy():
    """Serve the genealogy tree viewer."""
    return send_from_directory(STATIC_DIR, "genealogy_viewer.html")


def _save_generation_to_genealogy(
    parent_population_id: int,
    generation_num: int,
    branch_name: str,
    children: list,
    metadata: dict | None = None,
) -> int | None:
    """Save children to genealogy DB; return new population id or None on failure."""
    try:
        from ..data.genealogy_db import save_generation_result

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


@app.route("/api/evolve", methods=["POST"])
@api_try_except
def evolve():
    """
    Produce next generation (stateless). Selection, crossover, mutation.
    Body: {
        "parents": [...],
        "population_size": 12,  (optional, default from config)
        "elitism": false  (optional; if true, best parent is copied unchanged)
    }
    Returns { "children": [genome JSONs] }.
    """
    data = request.json or {}
    if "parents" not in data:
        return api_error(ERR_PARENTS_ARRAY_REQUIRED, 400)
    parents_data = data.get("parents", [])
    if not parents_data:
        return api_error(ERR_PARENTS_ARRAY_REQUIRED, 400)

    from ..evolution.config import (
        get_crossover_probability,
        get_elitism_default,
        get_population_size,
    )

    population_size = data.get("population_size", get_population_size())
    crossover_probability = data.get(
        "crossover_probability", get_crossover_probability()
    )
    elitism = data.get("elitism", get_elitism_default())
    parent_population_id = data.get("parent_population_id")
    generation_num = data.get("generation_num", 0)
    branch_name = data.get("branch_name", "main")

    parents_for_evolution = [
        {"genome": p.get("genome", p), "fitness": p.get("fitness", p.get("clicks", 0))}
        for p in parents_data
    ]
    substrate = get_current_substrate()
    children = produce_next_generation(
        substrate,
        parents_for_evolution,
        population_size=population_size,
        elitism=elitism,
        crossover_probability=crossover_probability,
    )

    new_pop_id = None
    if parent_population_id is not None:
        experiment_metadata = {
            "experiment_config": {
                "substrate_id": substrate.id,
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
        "output_type": substrate.output_type,
        "substrate_id": substrate.id,
    }
    if new_pop_id is not None:
        payload["population_id"] = new_pop_id
    return jsonify(payload)


@app.route("/api/save", methods=["POST"])
@api_try_except
def save_individual():
    """
    Save an individual (stateless). Supported for any substrate with save capability.
    Body: { "genome": { ... }, "id": 123 (optional), "visualize": true (optional) }
    """
    from ..substrate.protocol import get_substrate_capabilities

    caps = get_substrate_capabilities(substrate)
    if not caps.get("save", False):
        return api_error("Save is not supported for this substrate.", 501)
    data = request.json or {}
    genome_json = data.get("genome")
    individual_id = data.get("id")
    visualize = data.get("visualize", True)
    if not genome_json:
        return api_error(ERR_GENOME_REQUIRED_REQUEST_BODY, 400)
    ind = substrate.from_json(genome_json)
    ind_id = individual_id if individual_id is not None else getattr(ind, "key", 0)

    def to_png_bytes(arr):
        return base64.b64decode(numpy_to_png_base64(arr))

    assets = substrate.build_save_assets(
        ind, ind_id, to_png_bytes=to_png_bytes, visualize=visualize
    )
    if not assets:
        return api_error("Save not implemented for this substrate.", 501)
    names = substrate.get_save_filenames(ind_id)
    if os.environ.get("SAVE_TO_DISK", "").strip() in ("1", "true", "yes"):
        saved_dir = os.path.join(ROOT_DIR, "output", "saved")
        os.makedirs(saved_dir, exist_ok=True)
        for name, content in assets.items():
            with open(os.path.join(saved_dir, name), "wb") as f:
                f.write(content)
    return build_save_zip_response(ind_id, assets, names["zip"])


def _serve_saved_asset(individual_id: int, asset_key: str, mimetype: str):
    """Serve a saved asset by key (e.g. png, network_pdf) from output/saved."""
    names = substrate.get_save_filenames(individual_id)
    if asset_key not in names:
        return api_error("Asset not found", 404)
    path = os.path.join(ROOT_DIR, "output", "saved", names[asset_key])
    if not os.path.isfile(path):
        return api_error("File not found", 404)
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype=mimetype,
        as_attachment=False,
    )


@app.route("/api/saved/<int:individual_id>/network")
def serve_saved_network(individual_id):
    """Serve network visualization PDF for a saved pattern."""
    return _serve_saved_asset(individual_id, "network_pdf", "application/pdf")


@app.route("/api/saved/<int:individual_id>/image")
def serve_saved_image(individual_id):
    """Serve the rendered PNG for a saved pattern."""
    return _serve_saved_asset(individual_id, "png", "image/png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info("=" * 60)
    logger.info("EYECATCHER - Interactive Evolution Server")
    logger.info("Substrate: %s", substrate.id)
    logger.info("=" * 60)
    logger.info("Starting server... Open http://localhost:%s in your browser", port)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    app.run(debug=debug, port=port, host="0.0.0.0")

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

from flask import Flask, request, send_from_directory
from flask_cors import CORS

from .. import get_root_dir
from ..evolution import get_configured_substrate, warn_if_neat_pop_size_mismatch
from .api_helpers import (
    ERR_GENOME_REQUIRED_BODY,
    api_error,
    api_try_except,
    build_save_zip_response,
    numpy_to_png_base64,
)
from .community_routes import community_bp
from .evolve_api import evolve_bp
from .genealogy_routes import genealogy_bp
from .stateless_api import init_stateless_api, stateless_bp

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
substrate = get_configured_substrate()
warn_if_neat_pop_size_mismatch(substrate)

# Initialize and register API blueprints
init_stateless_api(substrate)
app.register_blueprint(stateless_bp)
app.register_blueprint(community_bp)
app.register_blueprint(evolve_bp)
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
        return api_error(ERR_GENOME_REQUIRED_BODY, 400)
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

"""
Interactive Evolution Server
Serves dual-CPPN population and handles evolution (stateless API only).

Each individual has two CPPNs:
- Visual: (x, y, distance, time, mouse_speed, mouse_dist, activity, bias) -> (R,G,B)
- Time: (raw_time, mouse_speed, mouse_dist, activity, bias) -> (modifiedTime)

Population state lives on the client; server provides compile, random, evolve, save.
Save returns file contents for client-side download (Railway / no server filesystem).

Where: Evolve in algorithm.reproduction; compile in glsl.ShaderCompiler;
save uses engine.render_dual_image and genome serialization.
"""

import base64
import io
import json
import logging
import os
import pickle

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .. import get_root_dir
from ..algorithm import (
    CROSSOVER_PROBABILITY,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_RENDER_RESOLUTION,
)
from ..algorithm import (
    config as evolution_config,
)
from ..algorithm.reproduction import produce_next_generation
from ..genome import DualGenome, dual_genome_from_json, dual_genome_to_json
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
from .response_builder import build_shader_response
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
substrate = evolution_config.get_configured_substrate()
# Backward compatibility: dual_cppn exposes engine and compiler for save/compile
engine = getattr(substrate, "engine", None)
compiler = getattr(substrate, "compiler", None)

# Initialize and register API blueprints
init_stateless_api(substrate, engine, compiler)
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


@app.route("/api/evolve", methods=["POST"])
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
    return _evolve_stateless(data)


def _evolve_stateless(data):
    """Evolve: parents in body, return children as JSONs; may save to genealogy."""
    try:
        parents_data = data.get("parents", [])
        population_size = data.get("population_size", DEFAULT_POPULATION_SIZE)
        elitism = data.get("elitism", False)
        parent_population_id = data.get("parent_population_id")
        generation_num = data.get("generation_num", 0)
        branch_name = data.get("branch_name", "main")

        if not parents_data:
            return api_error(ERR_PARENTS_ARRAY_REQUIRED, 400)

        children = produce_next_generation(
            substrate,
            parents_data,
            population_size=population_size,
            elitism=elitism,
            crossover_probability=CROSSOVER_PROBABILITY,
        )

        if parent_population_id is not None:
            try:
                from ..data.genealogy_db import save_generation_result

                new_pop_id = save_generation_result(
                    parent_population_id, generation_num, branch_name, children
                )
                if new_pop_id is not None:
                    return jsonify(
                        {
                            "children": children,
                            "population_id": new_pop_id,
                            "output_type": substrate.output_type,
                            "substrate_id": substrate.id,
                        }
                    )
            except Exception as e:
                logger.exception("Failed to save to genealogy: %s", e)
        return jsonify(
            {
                "children": children,
                "output_type": substrate.output_type,
                "substrate_id": substrate.id,
            }
        )
    except ValueError as e:
        logger.exception("Breed ValueError: %s", e)
        return api_error(f"Validation error: {str(e)}", 400)
    except Exception as e:
        logger.exception("Breed Exception: %s", e)
        return api_error(f"Server error: {str(e)}", 500)


@app.route("/api/save", methods=["POST"])
@api_try_except
def save_individual():
    """
    Save an individual (stateless). Supported for dual_cppn, single_cppn, ca.
    Body: {
        "genome": { ... },       (required)
        "id": 123,               (optional, defaults to genome.key)
        "visualize": true        (optional, default true; dual_cppn only, network PDF)
    }
    """
    from ..substrate.protocol import get_substrate_capabilities

    caps = get_substrate_capabilities(substrate)
    if not caps.get("save", False):
        return api_error(
            "Save is not supported for this substrate.",
            501,
        )
    data = request.json or {}
    genome_json = data.get("genome")
    individual_id = data.get("id")
    visualize = data.get("visualize", True)
    if not genome_json:
        return api_error(ERR_GENOME_REQUIRED_REQUEST_BODY, 400)
    if substrate.id == "dual_cppn" and engine is not None:
        dual_genome = dual_genome_from_json(
            genome_json, engine.config, engine.time_config
        )
        return _save_dual_genome(
            dual_genome, individual_id or dual_genome.key, visualize=visualize
        )
    ind = substrate.from_json(genome_json)
    ind_id = individual_id if individual_id is not None else getattr(ind, "key", 0)
    if substrate.id == "single_cppn":
        return _save_single_cppn(substrate, ind, ind_id)
    if substrate.id == "ca":
        return _save_ca(substrate, ind, ind_id)
    return api_error("Save not implemented for this substrate.", 501)


def get_saved_asset_filenames(individual_id: int):
    """
    Return logical filenames for saved assets (no directory prefix).

    Keys: png, glsl, bundle_json, genome_json, pkl, network_pdf, zip.
    Use when building zip or writing to output/saved.
    """
    return {
        "png": f"pattern_{individual_id}.png",
        "glsl": f"pattern_{individual_id}.glsl",
        "bundle_json": f"pattern_{individual_id}_bundle.json",
        "genome_json": f"genome_{individual_id}.json",
        "pkl": f"dual_genome_{individual_id}.pkl",
        "network_pdf": f"dual_genome_{individual_id}_network.pdf",
        "zip": f"pattern_{individual_id}.zip",
    }


def _save_dual_genome(
    dual_genome: DualGenome, individual_id: int, visualize: bool = True
):
    """
    Build save assets in memory and return them for client-side download.
    Works on Railway (no server filesystem). Optionally write to disk if SAVE_TO_DISK=1.
    """
    resp = build_shader_response(
        dual_genome,
        individual_id=individual_id,
        clicks=0,
        compiler=compiler,
        visual_config=engine.config,
        time_config=engine.time_config,
    )
    shader_code = resp["shader"]
    bundle = {
        "shader": shader_code,
        "metadata": {
            "type": "dual_cppn",
            "visual": {
                "num_nodes": resp["visual_nodes"],
                "num_connections": resp["visual_connections"],
            },
            "time_signal": {
                "num_nodes": resp["time_nodes"],
                "num_connections": resp["time_connections"],
            },
            "fitness": dual_genome.fitness,
        },
    }
    bundle_json = json.dumps(bundle, indent=2)
    genome_json = json.dumps(dual_genome_to_json(dual_genome), indent=2)

    img = engine.render_dual_image(
        dual_genome,
        resolution=DEFAULT_RENDER_RESOLUTION,
    )
    img_base64 = numpy_to_png_base64(img)
    pkl_buffer = io.BytesIO()
    pickle.dump(
        {
            "visual": dual_genome.visual,
            "time_signal": dual_genome.time_signal,
            "key": dual_genome.key,
        },
        pkl_buffer,
    )
    pkl_bytes = pkl_buffer.getvalue()
    pdf_bytes = None
    if visualize:
        from ..evaluation.genome_visualizer import render_genome_network_pdf

        pdf_buffer = io.BytesIO()
        pdf_bytes = render_genome_network_pdf(
            dual_genome.visual, engine.config, pdf_buffer
        )

    names = get_saved_asset_filenames(individual_id)
    assets = {
        names["png"]: base64.b64decode(img_base64),
        names["glsl"]: shader_code.encode("utf-8"),
        names["bundle_json"]: bundle_json.encode("utf-8"),
        names["genome_json"]: genome_json.encode("utf-8"),
        names["pkl"]: pkl_bytes,
    }
    if pdf_bytes:
        assets[names["network_pdf"]] = pdf_bytes

    if os.environ.get("SAVE_TO_DISK", "").strip() in ("1", "true", "yes"):
        saved_dir = os.path.join(ROOT_DIR, "output", "saved")
        os.makedirs(saved_dir, exist_ok=True)
        for name, data in assets.items():
            path = os.path.join(saved_dir, name)
            with open(path, "wb") as f:
                f.write(data)

    return build_save_zip_response(individual_id, assets, names["zip"])


def _save_single_cppn(substrate, ind, individual_id: int):
    """Save single-CPPN individual: shader, PNG, genome JSON."""
    from ..evaluation.rendering import render_image

    shader_code = substrate.compile_to_shader(ind)
    img = render_image(ind, substrate.config, resolution=DEFAULT_RENDER_RESOLUTION)
    img_base64 = numpy_to_png_base64(img)
    genome_json = json.dumps(substrate.to_json(ind), indent=2)
    names = {
        "png": f"pattern_{individual_id}.png",
        "glsl": f"pattern_{individual_id}.glsl",
        "genome_json": f"genome_{individual_id}.json",
        "zip": f"pattern_{individual_id}.zip",
    }
    assets = {
        names["png"]: base64.b64decode(img_base64),
        names["glsl"]: (shader_code or "").encode("utf-8"),
        names["genome_json"]: genome_json.encode("utf-8"),
    }
    return build_save_zip_response(individual_id, assets, names["zip"])


def _save_ca(substrate, ind, individual_id: int):
    """Save CA individual: rule JSON, PNG image."""
    out = substrate.evaluate(ind, {})
    if out.output_type != "grid" or not hasattr(out.data, "shape"):
        return api_error("CA evaluate failed", 500)
    arr = np.asarray(out.data)
    img_base64 = numpy_to_png_base64(arr)
    genome_json = json.dumps(substrate.to_json(ind), indent=2)
    names = {
        "png": f"pattern_{individual_id}.png",
        "genome_json": f"genome_{individual_id}.json",
        "zip": f"pattern_{individual_id}.zip",
    }
    assets = {
        names["png"]: base64.b64decode(img_base64),
        names["genome_json"]: genome_json.encode("utf-8"),
    }
    return build_save_zip_response(individual_id, assets, names["zip"])


@app.route("/api/saved/<int:individual_id>/network")
def serve_saved_network(individual_id):
    """Serve network visualization PDF for a saved pattern (genome visualizer)."""
    names = get_saved_asset_filenames(individual_id)
    path = os.path.join(ROOT_DIR, "output", "saved", names["network_pdf"])
    if not os.path.isfile(path):
        return api_error("Network visualization not found", 404)
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype="application/pdf",
        as_attachment=False,
    )


@app.route("/api/saved/<int:individual_id>/image")
def serve_saved_image(individual_id):
    """Serve the rendered PNG for a saved pattern."""
    names = get_saved_asset_filenames(individual_id)
    path = os.path.join(ROOT_DIR, "output", "saved", names["png"])
    if not os.path.isfile(path):
        return api_error("Image not found", 404)
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype="image/png",
        as_attachment=False,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info("=" * 60)
    logger.info("EYECATCHER - Interactive Evolution Server")
    logger.info("Dual-CPPN Mode: Visual + Time Signal Networks")
    logger.info("=" * 60)
    logger.info("Starting server... Open http://localhost:%s in your browser", port)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    app.run(debug=debug, port=port, host="0.0.0.0")

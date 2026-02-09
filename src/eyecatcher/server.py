"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding (stateless API only).

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)

Population state lives on the client; server provides compile, random, breed, save.
Save returns file contents for client-side download (Railway / no server filesystem).
"""

import base64
import io
import json
import logging
import os
import pickle
import random
import zipfile
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from . import get_root_dir
from .api_helpers import api_error
from .app_config import (
    DEFAULT_POPULATION_SIZE,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_TIME,
    MUTATION_PROBABILITY,
)
from .community_routes import community_bp
from .cppn_engine import (
    CPPNEngine,
    DualGenome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from .genealogy_routes import _init_genealogy_db, genealogy_bp
from .shader_compiler import ShaderCompiler
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
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# CORS: allow all in dev, or set CORS_ORIGINS env for production
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
if _cors_origins == "*":
    CORS(app)
else:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(",")])

# Engine and compiler (no server-side population state)
engine = CPPNEngine()
engine.create_population()  # Initialize NEAT populations for mutation/crossover
compiler = ShaderCompiler(
    color_mode="hsv"
)  # Use HSV output for more vibrant colors (client converts to RGB for display)
# compiler = ShaderCompiler(color_mode="rgb")  # Use RGB output

# Initialize and register API blueprints
init_stateless_api(engine, compiler)
_init_genealogy_db()  # Initialize genealogy database
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


@app.route("/api/breed", methods=["POST"])
def breed():
    """
    Breed next generation (stateless).
    Body: {
        "parents": [...],
        "population_size": 12,  (optional, default from config)
        "elitism": false  (optional; if true, best parent is copied unchanged)
    }
    Returns { "children": [genome JSONs] }.
    """
    data = request.json or {}
    if "parents" not in data:
        return api_error("parents array required", 400)
    return _breed_stateless(data)


def _breed_stateless(data):
    """Stateless breed: parents in body, return children as genome JSONs."""
    from .cppn_engine import copy_dual_genome, dual_genome_to_json

    try:
        parents_data = data.get("parents", [])
        population_size = data.get("population_size", DEFAULT_POPULATION_SIZE)
        elitism = data.get("elitism", False)

        # Genealogy metadata
        parent_population_id = data.get(
            "parent_population_id"
        )  # ID of parent generation
        generation_num = data.get("generation_num", 0)
        branch_name = data.get("branch_name", "main")

        if not parents_data:
            return api_error("parents array required", 400)
        parents = []
        for idx, p in enumerate(parents_data):
            try:
                genome_data = p.get("genome", p)
                dual = dual_genome_from_json(genome_data, engine)
                dual.fitness = p.get("clicks", 0)
                parents.append({"genome": dual, "clicks": p.get("clicks", 0)})
            except Exception as e:
                logger.warning(
                    "Failed to parse parent %s: %s. Parent data: %s", idx, e, p
                )
                continue
        if not parents:
            return jsonify(
                {"error": "No valid parents - check server logs for details"}
            ), 400
        max_key = max(p["genome"].key for p in parents)
        next_key = max_key + 1
        children = []
        # Elitism: optionally keep best parent unchanged
        if elitism:
            best = max(parents, key=lambda x: x["clicks"])
            elite = copy_dual_genome(best["genome"], engine, next_key)
            children.append(dual_genome_to_json(elite))
            next_key += 1
        while len(children) < population_size:
            if len(parents) == 1:
                child = engine.mutate_dual_genome(parents[0]["genome"], next_key)
            else:
                if random.random() < MUTATION_PROBABILITY:
                    parent = random.choice(parents)
                    child = engine.mutate_dual_genome(parent["genome"], next_key)
                else:
                    p1, p2 = random.sample(parents, 2)
                    child = engine.crossover_dual_genomes(
                        p1["genome"], p2["genome"], next_key
                    )
            children.append(dual_genome_to_json(child))
            next_key += 1

        # Auto-save to genealogy database (only if parent_population_id is provided)
        if parent_population_id is not None:
            try:
                from .genealogy_routes import _get_db

                conn = _get_db()
                try:
                    parent_row = conn.execute(
                        "SELECT generation_num FROM populations WHERE id = ?",
                        (parent_population_id,),
                    ).fetchone()
                    if not parent_row:
                        return jsonify({"children": children})
                    if generation_num != parent_row["generation_num"] + 1:
                        # Skip genealogy save; breeding still succeeds
                        return jsonify({"children": children})

                    cur = conn.execute(
                        """INSERT INTO populations
                           (parent_id, generation_num, created_at, branch_name,
                            description, user_id, population_size, metadata_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            parent_population_id,
                            generation_num,
                            datetime.utcnow().isoformat(),
                            branch_name,
                            f"Generation {generation_num}",
                            "user",
                            len(children),
                            "{}",
                        ),
                    )
                    new_population_id = cur.lastrowid

                    for idx, child_genome in enumerate(children):
                        genome_json = json.dumps(child_genome)
                        conn.execute(
                            """INSERT INTO individuals
                               (population_id, genome_key, genome_json,
                                fitness, created_at)
                               VALUES (?, ?, ?, ?, ?)""",
                            (
                                new_population_id,
                                child_genome.get("key", idx),
                                genome_json,
                                0,
                                datetime.utcnow().isoformat(),
                            ),
                        )

                    conn.commit()
                    return jsonify(
                        {"children": children, "population_id": new_population_id}
                    )
                finally:
                    conn.close()
            except Exception as e:
                logger.exception("Failed to save to genealogy: %s", e)
                return jsonify({"children": children})

        # Return children without genealogy tracking
        return jsonify({"children": children})
    except ValueError as e:
        logger.exception("Breed ValueError: %s", e)
        return api_error(f"Validation error: {str(e)}", 400)
    except Exception as e:
        logger.exception("Breed Exception: %s", e)
        return api_error(f"Server error: {str(e)}", 500)


@app.route("/api/save", methods=["POST"])
def save_individual():
    """
    Save a dual genome (stateless).
    Body: {
        "genome": { ... },       (required)
        "id": 123,               (optional, defaults to genome.key)
        "visualize": true        (optional, default true; generate network PDF)
    }
    """
    data = request.json or {}
    genome_json = data.get("genome")
    individual_id = data.get("id")
    visualize = data.get("visualize", True)
    if not genome_json:
        return api_error("genome required in request body", 400)
    try:
        dual_genome = dual_genome_from_json(genome_json, engine)
        return _save_dual_genome(
            dual_genome, individual_id or dual_genome.key, visualize=visualize
        )
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)


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
    shader_code = compiler.compile_dual_to_glsl(
        dual_genome, engine.config, engine.time_config
    )
    bundle = {
        "shader": shader_code,
        "metadata": {
            "type": "dual_cppn",
            "visual": {
                "num_nodes": len(dual_genome.visual.nodes),
                "num_connections": len(
                    [c for c in dual_genome.visual.connections.values() if c.enabled]
                ),
            },
            "time_signal": {
                "num_nodes": len(dual_genome.time_signal.nodes),
                "num_connections": len(
                    [
                        c
                        for c in dual_genome.time_signal.connections.values()
                        if c.enabled
                    ]
                ),
            },
            "fitness": dual_genome.fitness,
        },
    }
    bundle_json = json.dumps(bundle, indent=2)
    genome_json = json.dumps(dual_genome_to_json(dual_genome), indent=2)

    # PNG image
    from PIL import Image

    img = engine.render_image(
        dual_genome.visual,
        resolution=DEFAULT_RENDER_RESOLUTION,
        time=DEFAULT_RENDER_TIME,
    )
    img_buffer = io.BytesIO()
    Image.fromarray(img).save(img_buffer, format="PNG")
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode("ascii")

    # Pickle genome
    pkl_buffer = io.BytesIO()
    pickle.dump(
        {
            "visual": dual_genome.visual,
            "time_signal": dual_genome.time_signal,
            "key": dual_genome.key,
        },
        pkl_buffer,
    )
    pkl_base64 = base64.b64encode(pkl_buffer.getvalue()).decode("ascii")

    # Optional: network PDF
    pdf_bytes = None
    if visualize:
        try:
            from .genome_visualizer import GenomeVisualizer

            visualizer = GenomeVisualizer(engine.config)
            pdf_buffer = io.BytesIO()
            visualizer.visualize_genome(dual_genome.visual, pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()
        except Exception as e:
            logger.warning("Genome visualization failed: %s", e)

    # Package all assets into a single zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"pattern_{individual_id}.png", base64.b64decode(img_base64))
        zf.writestr(f"pattern_{individual_id}.glsl", shader_code.encode("utf-8"))
        zf.writestr(f"pattern_{individual_id}_bundle.json", bundle_json.encode("utf-8"))
        zf.writestr(f"genome_{individual_id}.json", genome_json.encode("utf-8"))
        zf.writestr(f"dual_genome_{individual_id}.pkl", base64.b64decode(pkl_base64))
        if pdf_bytes:
            zf.writestr(f"dual_genome_{individual_id}_network.pdf", pdf_bytes)
    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("ascii")

    downloads = [
        {
            "filename": f"pattern_{individual_id}.zip",
            "mime": "application/zip",
            "content_base64": zip_base64,
        },
    ]

    # Optional: write to disk for local dev (e.g. SAVE_TO_DISK=1)
    if os.environ.get("SAVE_TO_DISK", "").strip() in ("1", "true", "yes"):
        os.makedirs("output/saved", exist_ok=True)
        with open(f"output/saved/pattern_{individual_id}.png", "wb") as f:
            f.write(base64.b64decode(img_base64))
        with open(f"output/saved/pattern_{individual_id}.glsl", "w") as f:
            f.write(shader_code)
        with open(f"output/saved/pattern_{individual_id}_bundle.json", "w") as f:
            f.write(bundle_json)
        with open(f"output/saved/genome_{individual_id}.json", "w") as f:
            f.write(genome_json)
        with open(f"output/saved/dual_genome_{individual_id}.pkl", "wb") as f:
            f.write(base64.b64decode(pkl_base64))
        if pdf_bytes:
            with open(
                f"output/saved/dual_genome_{individual_id}_network.pdf", "wb"
            ) as f:
                f.write(pdf_bytes)

    return jsonify(
        {
            "id": individual_id,
            "status": "saved",
            "downloads": downloads,
        }
    )


@app.route("/api/saved/<int:individual_id>/network")
def serve_saved_network(individual_id):
    """Serve network visualization PDF for a saved pattern (genome visualizer)."""
    path = os.path.join(
        ROOT_DIR, "output", "saved", f"dual_genome_{individual_id}_network.pdf"
    )
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
    path = os.path.join(ROOT_DIR, "output", "saved", f"pattern_{individual_id}.png")
    if not os.path.isfile(path):
        return api_error("Image not found", 404)
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype="image/png",
        as_attachment=False,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info("=" * 60)
    logger.info("EYECATCHER - Interactive Evolution Server")
    logger.info("Dual-CPPN Mode: Visual + Time Signal Networks")
    logger.info("=" * 60)
    logger.info("Starting server... Open http://localhost:%s in your browser", port)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    app.run(debug=debug, port=port, host="0.0.0.0")

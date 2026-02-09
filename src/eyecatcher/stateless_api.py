"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state:
- /api/compile: Compile genome JSON to GLSL shaders
- /api/random: Generate random population as genome JSON
"""

from flask import Blueprint, jsonify, request

from .api_helpers import api_error
from .app_config import DEFAULT_POPULATION_SIZE, MAX_POPULATION_SIZE
from .cppn_engine import CPPNEngine, DualGenome, create_random_dual_genome
from .genome_serialization import (
    dual_genome_from_json,
    dual_genome_network_stats,
    dual_genome_to_json,
)
from .shader_compiler import ShaderCompiler

# Create blueprint
stateless_bp = Blueprint("stateless", __name__)

# Module-level references (set by init_stateless_api)
_engine: CPPNEngine = None
_compiler: ShaderCompiler = None


def init_stateless_api(engine: CPPNEngine, compiler: ShaderCompiler):
    """
    Initialize the stateless API with engine and compiler references.
    Call this before registering the blueprint with the app.
    """
    global _engine, _compiler
    _engine = engine
    _compiler = compiler


def _shader_response_for_dual(
    dual_genome: DualGenome,
    individual_id: int,
    clicks: int = 0,
    compiler=None,
):
    """Build shader response dict for a dual genome. Uses compiler or _compiler."""
    comp = compiler if compiler is not None else _compiler
    shader_code = comp.compile_dual_to_glsl(
        dual_genome, _engine.config, _engine.time_config
    )
    stats = dual_genome_network_stats(dual_genome)
    return {
        "id": individual_id,
        "shader": shader_code,
        "clicks": clicks,
        "nodes": stats["visual_nodes"] + stats["time_nodes"],
        "connections": stats["visual_connections"] + stats["time_connections"],
        "visual_nodes": stats["visual_nodes"],
        "visual_connections": stats["visual_connections"],
        "time_nodes": stats["time_nodes"],
        "time_connections": stats["time_connections"],
    }


@stateless_bp.route("/api/compile", methods=["POST"])
def api_compile():
    """
    Stateless: compile a list of dual genomes to shaders.
    Body: { "genomes": [ ... ], "color_mode": "hsv"|"rgb" (optional) }
    Returns: { "shaders": [ { "id", "shader", "clicks", "nodes", ... }, ... ] }
    """
    try:
        data = request.json or {}
        genomes_data = data.get("genomes", [])
        if not genomes_data:
            return api_error("genomes array required", 400)
        color_mode = (data.get("color_mode") or "").strip().lower()
        if color_mode and color_mode not in ("hsv", "rgb"):
            color_mode = "hsv"
        compiler = (
            _compiler
            if (not color_mode or color_mode == _compiler.color_mode)
            else ShaderCompiler(color_mode=color_mode)
        )
        shaders = []
        for i, g_data in enumerate(genomes_data):
            dual = dual_genome_from_json(g_data, _engine)
            individual_id = g_data.get("key", dual.key if dual else i)
            clicks = g_data.get("clicks", 0)
            shaders.append(
                _shader_response_for_dual(
                    dual, individual_id, clicks, compiler=compiler
                )
            )
        return jsonify({"shaders": shaders})
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/random", methods=["POST"])
def api_random():
    """
    Stateless: create a new random population.
    Body: { "size": N } (default from config)
    Returns: { "genomes": [ { "key", "visual", "time_signal" }, ... ] }
    """
    try:
        data = request.json or {}
        size = data.get("size", DEFAULT_POPULATION_SIZE)
        size = max(1, min(int(size), MAX_POPULATION_SIZE))
        genomes = []
        for i in range(size):
            dual = create_random_dual_genome(_engine, genome_id=i)
            genomes.append(dual_genome_to_json(dual))
        return jsonify({"genomes": genomes})
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/time-output", methods=["POST"])
def api_time_output():
    """
    Stateless: query the Time CPPN for a genome with given inputs (for debug panel).
    Body: { "genome": { ... }, "time", "mouseSpeed", "mouseDist", "activity" } (0-1).
    Returns: { "timeOutput": float, "inputs": { ... } }.
    """
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error("genome required", 400)
        raw_time = float(data.get("time", 0))
        mouse_speed = float(data.get("mouseSpeed", 0))
        mouse_dist = float(data.get("mouseDist", 0))
        activity = float(data.get("activity", 0))
        dual = dual_genome_from_json(genome_data, _engine)
        raw_time_n = raw_time * 2.0 - 1.0
        mouse_speed_n = mouse_speed * 2.0 - 1.0
        mouse_dist_n = mouse_dist * 2.0 - 1.0
        activity_n = activity * 2.0 - 1.0
        time_output = _engine.query_time_signal(
            dual.time_signal, raw_time_n, mouse_speed_n, mouse_dist_n, activity_n
        )
        return jsonify(
            {
                "timeOutput": time_output,
                "inputs": {
                    "rawTime": raw_time,
                    "mouseSpeed": mouse_speed,
                    "mouseDist": mouse_dist,
                    "activity": activity,
                },
            }
        )
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/network", methods=["POST"])
def api_network():
    """
    Stateless: get network visualization data for a genome.
    Body: { "genome": { "key", "visual", "time_signal" } }
    Returns: { "id": key, "nodes": [...], "connections": [...] }
    """
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error("genome required", 400)

        dual = dual_genome_from_json(genome_data, _engine)
        individual_id = genome_data.get("key", dual.key if dual else 0)

        all_nodes = []
        all_connections = []

        # Extract visual network
        if dual.visual:
            from .genome_serialization import extract_network_data

            visual_nodes, visual_conns = extract_network_data(
                dual.visual, "visual", _engine.config
            )
            all_nodes.extend(visual_nodes)
            all_connections.extend(visual_conns)

        # Extract time signal network
        if dual.time_signal:
            from .genome_serialization import extract_network_data

            time_nodes, time_conns = extract_network_data(
                dual.time_signal, "time", _engine.time_config
            )
            all_nodes.extend(time_nodes)
            all_connections.extend(time_conns)

        return jsonify(
            {
                "id": individual_id,
                "nodes": all_nodes,
                "connections": all_connections,
                "status": "success",
            }
        )
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/adjust-weight", methods=["POST"])
def api_adjust_weight():
    """
    Stateless: adjust a connection weight in a genome and return updated shader.
    Body: {
        "genome": { "key", "visual", "time_signal" },
        "network": "visual" or "time",
        "source": source_node_id (string like "visual_input_-1"),
        "target": target_node_id (string like "visual_hidden_5"),
        "weight": new_weight_value (float)
    }
    Returns: { "status": "success", "shader": "...", "genome": {...} }
    """
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error("genome required", 400)

        network_type = data.get("network")  # 'visual' or 'time'
        source_node = data.get("source")
        target_node = data.get("target")
        new_weight = float(data.get("weight", 0))

        # Parse the genome
        dual = dual_genome_from_json(genome_data, _engine)

        # Select the appropriate network
        if network_type == "visual":
            genome = dual.visual
        elif network_type == "time":
            genome = dual.time_signal
        else:
            return api_error(f"Unknown network type: {network_type}", 400)

        # Convert node IDs from strings to integers
        # Frontend sends IDs like "visual_input_-1" or "time_hidden_5"
        def extract_node_id(node_id_str):
            parts = node_id_str.split("_")
            if len(parts) >= 3:
                return int(parts[-1])  # Last part is the numeric ID
            return int(node_id_str)

        try:
            source_id = extract_node_id(source_node)
            target_id = extract_node_id(target_node)
        except (ValueError, IndexError):
            return jsonify(
                {"error": f"Invalid node ID format: {source_node} or {target_node}"}
            ), 400

        # Update the weight in the connection
        conn_key = (source_id, target_id)
        if conn_key in genome.connections:
            genome.connections[conn_key].weight = new_weight

            # Recompile shader with updated weights
            shader_code = _compiler.compile_dual_to_glsl(
                dual, _engine.config, _engine.time_config
            )

            # Return updated genome as JSON so client can update its state
            from .genome_serialization import dual_genome_to_json

            updated_genome = dual_genome_to_json(dual)

            return jsonify(
                {
                    "status": "success",
                    "shader": shader_code,
                    "genome": updated_genome,
                    "network": network_type,
                    "source": source_node,
                    "target": target_node,
                    "weight": new_weight,
                }
            )
        else:
            return api_error(
                f"Connection not found: {conn_key} ({source_node} -> {target_node})",
                404,
            )

    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)

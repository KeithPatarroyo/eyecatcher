"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state.
Blueprint is registered in server; engine and compiler are injected via
init_stateless_api. Endpoints: /api/compile, /api/random, /api/evaluate,
/api/time-output, /api/network, /api/adjust-weight.
"""

import numpy as np
from flask import Blueprint, jsonify, request

from ..algorithm import DEFAULT_POPULATION_SIZE, MAX_POPULATION_SIZE
from ..evaluation import extract_network_data, parse_network_node_id
from ..genome import dual_genome_from_json, dual_genome_to_json
from ..signals import TIME_INPUTS
from .api_helpers import (
    ERR_GENOME_REQUIRED,
    ERR_GENOMES_ARRAY_REQUIRED,
    api_error,
    api_try_except,
    numpy_to_png_base64,
)

# Create blueprint
stateless_bp = Blueprint("stateless", __name__)

# Module-level references (set by init_stateless_api)
_substrate = None
_engine = None
_compiler = None


def init_stateless_api(substrate, engine=None, compiler=None):
    """
    Initialize the stateless API with substrate and optional engine/compiler.

    Substrate is the active evolvable (dual_cppn, etc.). Engine and compiler
    are set for dual_cppn for shader response building; other substrates may
    leave them None.
    """
    global _substrate, _engine, _compiler
    _substrate = substrate
    _engine = engine
    _compiler = compiler


@stateless_bp.route("/api/config", methods=["GET"])
def api_config():
    """
    Return current experiment config for bootstrap (substrate, output type,
    population limits, capabilities). GET /api/config → substrate_id,
    output_type, population_size, max_population_size, capabilities.
    """
    if _substrate is None:
        return api_error("No substrate configured.", 503)
    from ..substrate.protocol import get_substrate_capabilities

    capabilities = get_substrate_capabilities(_substrate)
    return jsonify(
        {
            "substrate_id": _substrate.id,
            "output_type": _substrate.output_type,
            "population_size": DEFAULT_POPULATION_SIZE,
            "max_population_size": MAX_POPULATION_SIZE,
            "capabilities": capabilities,
        }
    )


def _require_capability(cap: str):
    """Error if substrate does not have the given capability."""
    from ..substrate.protocol import get_substrate_capabilities

    caps = get_substrate_capabilities(_substrate)
    if not caps.get(cap, False):
        return api_error(
            f"This endpoint requires a substrate with '{cap}' capability.",
            501,
        )
    return None


def _require_dual_genome_from_request(cap: str):
    """
    Require capability, parse JSON, require genome, deserialize to DualGenome.
    Returns (dual, individual_id, clicks, err). If err is not None, return it.
    """
    err = _require_capability(cap)
    if err is not None:
        return None, None, None, err
    data = request.json or {}
    genome_data = data.get("genome")
    if not genome_data:
        return None, None, None, api_error(ERR_GENOME_REQUIRED, 400)
    dual = dual_genome_from_json(genome_data, _engine.config, _engine.time_config)
    individual_id, clicks = _extract_genome_id_clicks(
        genome_data, dual.key if dual else 0
    )
    return dual, individual_id, clicks, None


def _extract_genome_id_clicks(g_data, default_key):
    """Return (individual_id, clicks) from genome JSON and default key."""
    return (g_data.get("key", default_key), g_data.get("clicks", 0))


def _compile_genomes(genomes_data, color_mode):
    """Compile genome JSONs to shader response dicts via the substrate protocol."""
    # Use a color-mode-specific compiler if the substrate owns one and mode differs
    compile_fn = _substrate.compile_to_shader
    if color_mode and _compiler and color_mode != _compiler.color_mode:
        from ..glsl import ShaderCompiler

        alt = ShaderCompiler(color_mode=color_mode)
        if hasattr(_substrate, "config"):

            def compile_fn(ind):
                return alt.compile_to_glsl(ind, _substrate.config)
        elif hasattr(_substrate, "engine"):

            def compile_fn(ind):
                return alt.compile_dual_to_glsl(
                    ind,
                    _substrate.engine.config,
                    _substrate.engine.time_config,
                )

    shaders = []
    for i, g_data in enumerate(genomes_data):
        ind = _substrate.from_json(g_data)
        individual_id, clicks = _extract_genome_id_clicks(
            g_data, getattr(ind, "key", i)
        )
        glsl = compile_fn(ind)
        resp = {
            "id": individual_id,
            "shader": glsl or "",
            "clicks": clicks,
        }
        stats = _substrate.get_compile_stats(ind)
        if stats:
            resp["visual_nodes"] = stats.get("visual_nodes", 0)
            resp["visual_connections"] = stats.get("visual_connections", 0)
            resp["time_nodes"] = stats.get("time_nodes", 0)
            resp["time_connections"] = stats.get("time_connections", 0)
            resp["nodes"] = resp["visual_nodes"] + resp["time_nodes"]
            resp["connections"] = resp["visual_connections"] + resp["time_connections"]
        else:
            resp["nodes"] = (
                len(getattr(ind, "nodes", {})) if hasattr(ind, "nodes") else 0
            )
            resp["connections"] = (
                len(getattr(ind, "connections", {}))
                if hasattr(ind, "connections")
                else 0
            )
        shaders.append(resp)
    return shaders


def _require_can_compile():
    """Error if substrate cannot compile genomes to shaders."""
    if not callable(getattr(_substrate, "compile_to_shader", None)):
        return api_error(
            "This endpoint requires a substrate that implements compile_to_shader.",
            501,
        )
    return None


@stateless_bp.route("/api/compile", methods=["POST"])
@api_try_except
def api_compile():
    """
    Stateless: compile genomes to shaders.
    Body: { "genomes": [ ... ], "color_mode": "hsv"|"rgb" (optional) }
    Returns: { "shaders": [ { "id", "shader", "clicks", "nodes", ... }, ... ] }
    Works for any substrate with compile_to_shader (dual_cppn, single_cppn, ca).
    """
    err = _require_can_compile()
    if err is not None:
        return err
    data = request.json or {}
    genomes_data = data.get("genomes", [])
    if not genomes_data:
        return api_error(ERR_GENOMES_ARRAY_REQUIRED, 400)
    color_mode = (data.get("color_mode") or "").strip().lower()
    if color_mode and color_mode not in ("hsv", "rgb"):
        color_mode = "hsv"
    shaders = _compile_genomes(genomes_data, color_mode)
    return jsonify({"shaders": shaders})


@stateless_bp.route("/api/random", methods=["POST"])
@api_try_except
def api_random():
    """
    Stateless: create a new random population.

    Body: { "size": N } (default from config)
    Returns: { "genomes": [ ... ], "output_type": "shader"|"grid"|... }
    Genome shape depends on substrate (dual_cppn: visual/time_signal; ca: rule, key).
    """
    data = request.json or {}
    size = data.get("size", DEFAULT_POPULATION_SIZE)
    size = max(1, min(int(size), MAX_POPULATION_SIZE))
    genomes = []
    for i in range(size):
        ind = _substrate.create_random(key=i)
        genomes.append(_substrate.to_json(ind))
    return jsonify(
        {
            "genomes": genomes,
            "output_type": _substrate.output_type,
            "substrate_id": _substrate.id,
        }
    )


@stateless_bp.route("/api/evaluate", methods=["POST"])
@api_try_except
def api_evaluate():
    """
    Evaluate genomes with the current substrate and return displayable output.

    Body: { "genomes": [ ... ] } (each item is substrate-specific genome JSON).
    Returns: { "results": [ { "id", "output_type", "image"?, "shader"? } ],
        "output_type" }. Grid has "image"; shader has "shader".
    """
    data = request.json or {}
    genomes_data = data.get("genomes", [])
    if not genomes_data:
        return api_error(ERR_GENOMES_ARRAY_REQUIRED, 400)
    results = []
    for i, g_data in enumerate(genomes_data):
        ind = _substrate.from_json(g_data)
        individual_id, _ = _extract_genome_id_clicks(g_data, getattr(ind, "key", i))
        out = _substrate.evaluate(ind, {})
        item = {"id": individual_id, "output_type": out.output_type}
        if out.output_type == "grid" and hasattr(out.data, "shape"):
            arr = np.asarray(out.data)
            b64 = numpy_to_png_base64(arr)
            item["image"] = "data:image/png;base64," + b64
        elif out.output_type == "shader" and isinstance(out.data, str):
            item["shader"] = out.data
        glsl = _substrate.compile_to_shader(ind)
        if glsl:
            item["shader"] = glsl
            if hasattr(ind, "rule"):
                item["rule"] = int(ind.rule)
        results.append(item)
    return jsonify(
        {
            "results": results,
            "output_type": _substrate.output_type,
            "substrate_id": _substrate.id,
        }
    )


@stateless_bp.route("/api/time-output", methods=["POST"])
@api_try_except
def api_time_output():
    """
    Stateless: query the Time CPPN for a genome with given inputs (for debug panel).
    Body: { "genome": { ... }, <id>: value ... } for each time CPPN input.
    Returns: { "timeOutput": float, "inputs": { <id>: value ... } }.
    """
    dual, _, _, err = _require_dual_genome_from_request("time_output")
    if err is not None:
        return err
    data = request.json or {}
    time_inputs = {}
    response_inputs = {}
    for s in TIME_INPUTS:
        raw_val = data.get(s.id)
        if raw_val is None and s.id == "raw_time":
            raw_val = data.get("time")
        val = float(raw_val if raw_val is not None else s.default)
        time_inputs[s.id] = val * 2.0 - 1.0
        response_inputs[s.id] = val
    time_output = _engine.query_time_signal(dual.time_signal, time_inputs)
    return jsonify({"timeOutput": time_output, "inputs": response_inputs})


@stateless_bp.route("/api/network", methods=["POST"])
@api_try_except
def api_network():
    """
    Stateless: get network visualization data for a genome.
    Body: { "genome": { "key", "visual", "time_signal" } }
    Returns: { "id": key, "nodes": [...], "connections": [...] }
    """
    dual, individual_id, _, err = _require_dual_genome_from_request("network")
    if err is not None:
        return err
    all_nodes = []
    all_connections = []

    # Extract visual network
    if dual.visual:
        visual_nodes, visual_conns = extract_network_data(
            dual.visual, "visual", _engine.config
        )
        all_nodes.extend(visual_nodes)
        all_connections.extend(visual_conns)

    # Extract time signal network
    if dual.time_signal:
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


@stateless_bp.route("/api/adjust-weight", methods=["POST"])
@api_try_except
def api_adjust_weight():
    """
    Stateless: adjust a connection weight in a genome and return updated shader.
    Body: { "genome": {...}, "network": "visual"|"time", "source", "target", "weight" }
    Returns: { "status": "success", "shader": "...", "genome": {...} }
    """
    dual, _, _, err = _require_dual_genome_from_request("adjust_weight")
    if err is not None:
        return err
    data = request.json or {}
    network_type = data.get("network")
    source_node = data.get("source")
    target_node = data.get("target")
    new_weight = float(data.get("weight", 0))

    # Select the appropriate network
    if network_type == "visual":
        genome = dual.visual
    elif network_type == "time":
        genome = dual.time_signal
    else:
        return api_error(f"Unknown network type: {network_type}", 400)

    try:
        source_id = parse_network_node_id(source_node)
        target_id = parse_network_node_id(target_node)
    except (ValueError, IndexError):
        return api_error(f"Invalid node ID format: {source_node} or {target_node}", 400)

    # Update the weight in the connection
    conn_key = (source_id, target_id)
    if conn_key in genome.connections:
        genome.connections[conn_key].weight = new_weight

        # Recompile shader with updated weights
        shader_code = _compiler.compile_dual_to_glsl(
            dual, _engine.config, _engine.time_config
        )

        # Return updated genome as JSON so client can update its state
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
    return api_error(
        f"Connection not found: {conn_key} ({source_node} -> {target_node})",
        404,
    )

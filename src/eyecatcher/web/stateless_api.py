"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state.
Blueprint is registered in server; substrate is injected via init_stateless_api.
Endpoints: /api/compile, /api/random, /api/evaluate,
/api/time-output, /api/network, /api/adjust-weight.
"""

import numpy as np
from flask import Blueprint, jsonify, request

from ..algorithm import DEFAULT_POPULATION_SIZE, MAX_POPULATION_SIZE
from ..signals import parse_time_inputs
from .api_helpers import (
    ERR_GENOME_REQUIRED,
    ERR_GENOMES_ARRAY_REQUIRED,
    api_error,
    api_try_except,
    numpy_to_png_base64,
)

# Create blueprint
stateless_bp = Blueprint("stateless", __name__)

# Module-level reference (set by init_stateless_api)
_substrate = None


def init_stateless_api(substrate):
    """
    Initialize the stateless API with the active substrate.

    Substrate is the active evolvable (dual_cppn, single_cppn, ca, etc.).
    """
    global _substrate
    _substrate = substrate


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


def _require_genome_from_request(cap: str):
    """
    Require capability, parse JSON, require genome, deserialize via substrate.
    Returns (ind, individual_id, clicks, err). If err is not None, return it.
    """
    err = _require_capability(cap)
    if err is not None:
        return None, None, None, err
    data = request.json or {}
    genome_data = data.get("genome")
    if not genome_data:
        return None, None, None, api_error(ERR_GENOME_REQUIRED, 400)
    try:
        ind, individual_id, clicks = _parse_one_genome(genome_data, 0)
    except Exception:
        return None, None, None, api_error("Invalid genome payload.", 400)
    return ind, individual_id, clicks, None


def _extract_genome_id_clicks(g_data, default_key):
    """Return (individual_id, clicks) from genome JSON and default key."""
    return (g_data.get("key", default_key), g_data.get("clicks", 0))


def _parse_one_genome(g_data: dict, index: int):
    """Deserialize one genome payload; return (ind, individual_id, clicks)."""
    ind = _substrate.from_json(g_data)
    individual_id, clicks = _extract_genome_id_clicks(
        g_data, getattr(ind, "key", index)
    )
    return ind, individual_id, clicks


def _compile_genomes(genomes_data, color_mode):
    """Compile genome JSONs to shader response dicts via the substrate protocol."""
    mode = (color_mode or "").strip().lower() or None
    shaders = []
    for i, g_data in enumerate(genomes_data):
        ind, individual_id, clicks = _parse_one_genome(g_data, i)
        glsl = _substrate.compile_to_shader(ind, color_mode=mode)
        resp = {
            "id": individual_id,
            "shader": glsl or "",
            "clicks": clicks,
        }
        stats = _substrate.get_compile_stats(ind)
        if stats:
            resp.update(stats)
            resp["nodes"] = sum(v for k, v in stats.items() if k.endswith("_nodes"))
            resp["connections"] = sum(
                v for k, v in stats.items() if k.endswith("_connections")
            )
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
        ind, individual_id, _ = _parse_one_genome(g_data, i)
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
    Stateless: query time/signal output for a genome with given inputs (debug panel).
    Body: { "genome": <substrate-specific JSON>, <signal_id>: value ... }.
    Returns: { "timeOutput": float, "inputs": { <id>: value ... } }.
    """
    ind, _, _, err = _require_genome_from_request("time_output")
    if err is not None:
        return err
    data = request.json or {}
    inputs = parse_time_inputs(data, bipolar=False)
    result = _substrate.query_time_output(ind, inputs)
    if result is None:
        return api_error("Time output not supported by this substrate.", 501)
    return jsonify(result)


@stateless_bp.route("/api/network", methods=["POST"])
@api_try_except
def api_network():
    """
    Stateless: get network visualization data for a genome.
    Body: { "genome": <substrate-specific JSON> }
    Returns: { "id": key, "nodes": [...], "connections": [...] }
    """
    ind, individual_id, _, err = _require_genome_from_request("network")
    if err is not None:
        return err
    result = _substrate.get_network_data(ind)
    if result is None:
        return api_error("Network visualization not supported by this substrate.", 501)
    return jsonify(
        {
            "id": individual_id,
            "nodes": result["nodes"],
            "connections": result["connections"],
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
    ind, _, _, err = _require_genome_from_request("adjust_weight")
    if err is not None:
        return err
    data = request.json or {}
    network_type = data.get("network")
    source_node = data.get("source")
    target_node = data.get("target")
    new_weight = float(data.get("weight", 0))
    result = _substrate.adjust_weight(
        ind, network_type, source_node, target_node, new_weight
    )
    if result is None:
        return api_error("Connection not found or invalid node ID.", 404)
    return jsonify(
        {
            "status": "success",
            "shader": result["shader"],
            "genome": result["genome"],
            "network": network_type,
            "source": source_node,
            "target": target_node,
            "weight": new_weight,
        }
    )

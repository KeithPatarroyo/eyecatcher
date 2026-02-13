"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state.
Representation is stored on Flask app.config["EYECATCHER_REPRESENTATION"].
Endpoints: /api/compile, /api/random, /api/evaluate,
/api/time-output, /api/network, /api/adjust-weight.
"""

import numpy as np
from flask import Blueprint, current_app, jsonify, request

from ..evolution import (
    get_crossover_probability,
    get_max_population_size,
    get_population_size,
    update_runtime_config,
)
from ..representation import get_representation
from ..representation.registry import REPRESENTATIONS
from ..signals import NETWORK_SIGNALS, parse_time_inputs
from .api_helpers import (
    ERR_INDIVIDUAL_REQUIRED,
    ERR_INDIVIDUALS_ARRAY_REQUIRED,
    api_error,
    api_try_except,
    numpy_to_png_base64,
)

# Create blueprint
stateless_bp = Blueprint("stateless", __name__)

# Config key for app-scoped representation
_REPRESENTATION_CONFIG_KEY = "EYECATCHER_REPRESENTATION"


def get_current_representation():
    """Current representation (from app config; updated by PATCH /api/config)."""
    return current_app.config.get(_REPRESENTATION_CONFIG_KEY)


def _config_response():
    """Build JSON config payload (representation, limits, capabilities)."""
    from ..representation.protocol import get_representation_capabilities

    representation = get_current_representation()
    capabilities = get_representation_capabilities(representation)
    payload = {
        "representation_id": representation.id,
        "output_type": representation.output_type,
        "population_size": get_population_size(),
        "max_population_size": get_max_population_size(),
        "crossover_probability": get_crossover_probability(),
        "capabilities": capabilities,
        "available_representation_ids": list(REPRESENTATIONS.keys()),
    }
    return jsonify(payload)


@stateless_bp.route("/api/config", methods=["GET", "PATCH"])
def api_config():
    """
    GET: current experiment config (respects runtime overlay).
    PATCH: update at runtime. Body: population_size?, max_population_size?,
        crossover_probability?, representation_id?. Same shape as GET.
    Changing representation_id updates app.config; client should clear grid.
    """
    if get_current_representation() is None:
        return api_error("No representation configured.", 503)
    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}
        new_id = data.get("representation_id")
        if new_id is not None:
            if new_id not in REPRESENTATIONS:
                return api_error(
                    f"Unknown representation: {new_id}. "
                    f"Available: {list(REPRESENTATIONS)}",
                    400,
                )
            current_app.config[_REPRESENTATION_CONFIG_KEY] = get_representation(new_id)
        update_runtime_config(data)
    return _config_response()


def _require_capability(cap: str):
    """Error if representation does not have the given capability."""
    from ..representation.protocol import get_representation_capabilities

    caps = get_representation_capabilities(get_current_representation())
    if not caps.get(cap, False):
        return api_error(
            f"This endpoint requires a representation with '{cap}' capability.",
            501,
        )
    return None


def _require_individual_from_request(cap: str):
    """
    Require capability, parse JSON, require individual, deserialize via representation.
    Returns (ind, individual_id, clicks, err). If err is not None, return it.
    """
    err = _require_capability(cap)
    if err is not None:
        return None, None, None, err
    data = request.json or {}
    individual_data = data.get("individual")
    if not individual_data:
        return None, None, None, api_error(ERR_INDIVIDUAL_REQUIRED, 400)
    try:
        ind, individual_id, clicks = _parse_one_individual(individual_data, 0)
    except Exception:
        return None, None, None, api_error("Invalid individual payload.", 400)
    return ind, individual_id, clicks, None


def _extract_individual_id_clicks(payload: dict, default_key: int):
    """Return (individual_id, clicks) from individual JSON and default key."""
    return (payload.get("key", default_key), payload.get("clicks", 0))


def _parse_one_individual(payload: dict, index: int):
    """Deserialize one individual payload; return (ind, individual_id, clicks)."""
    ind = get_current_representation().from_json(payload)
    individual_id, clicks = _extract_individual_id_clicks(
        payload, getattr(ind, "key", index)
    )
    return ind, individual_id, clicks


def _compile_individuals(individuals_data, color_mode):
    """Compile individual JSONs to shader response dicts via representation protocol."""
    mode = (color_mode or "").strip().lower() or None
    shaders = []
    for i, item_data in enumerate(individuals_data):
        ind, individual_id, clicks = _parse_one_individual(item_data, i)
        glsl = get_current_representation().compile_to_shader(ind, color_mode=mode)
        resp = {
            "id": individual_id,
            "shader": glsl or "",
            "clicks": clicks,
        }
        stats = get_current_representation().get_compile_stats(ind)
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
    """Error if representation cannot compile genomes to shaders."""
    if not callable(getattr(get_current_representation(), "compile_to_shader", None)):
        return api_error(
            "This endpoint requires a representation that implements "
            "compile_to_shader.",
            501,
        )
    return None


@stateless_bp.route("/api/compile", methods=["POST"])
@api_try_except
def api_compile():
    """
    Stateless: compile individuals to shaders.
    Body: { "individuals": [ ... ], "color_mode": "hsv"|"rgb" (optional) }
    Returns: { "shaders": [ { "id", "shader", "clicks", "nodes", ... }, ... ] }
    Works for any representation with compile_to_shader (dual_cppn, single_cppn, ca).
    """
    err = _require_can_compile()
    if err is not None:
        return err
    data = request.json or {}
    individuals_data = data.get("individuals", [])
    if not individuals_data:
        return api_error(ERR_INDIVIDUALS_ARRAY_REQUIRED, 400)
    color_mode = (data.get("color_mode") or "").strip().lower()
    if color_mode and color_mode not in ("hsv", "rgb"):
        color_mode = "hsv"
    shaders = _compile_individuals(individuals_data, color_mode)
    return jsonify({"shaders": shaders})


@stateless_bp.route("/api/random", methods=["POST"])
@api_try_except
def api_random():
    """
    Stateless: create a new random population.

    Body: { "size": N } (default from config)
    Returns: { "individuals": [ ... ], "output_type": "shader"|"grid"|... }
    Individual shape depends on representation (dual_cppn: visual/time_signal;
    ca: grid, key).
    """
    data = request.json or {}
    size = data.get("size", get_population_size())
    size = max(1, min(int(size), get_max_population_size()))
    individuals = []
    rep = get_current_representation()
    for i in range(size):
        ind = rep.create_random(key=i)
        individuals.append(rep.to_json(ind))
    return jsonify(
        {
            "individuals": individuals,
            "output_type": rep.output_type,
            "representation_id": rep.id,
        }
    )


@stateless_bp.route("/api/evaluate", methods=["POST"])
@stateless_bp.route("/api/express", methods=["POST"])
@api_try_except
def api_evaluate():
    """
    Express individuals with the current representation and return displayable output.

    Body: { "individuals": [ ... ] } (each item is representation-specific JSON).
    Returns: { "results": [ { "id", "output_type", "image"?, "shader"? } ],
        "output_type" }. Grid has "image"; shader has "shader".
    """
    data = request.json or {}
    individuals_data = data.get("individuals", [])
    if not individuals_data:
        return api_error(ERR_INDIVIDUALS_ARRAY_REQUIRED, 400)
    results = []
    for i, item_data in enumerate(individuals_data):
        ind, individual_id, _ = _parse_one_individual(item_data, i)
        out = get_current_representation().express(ind, {})
        item = {"id": individual_id, "output_type": out.output_type}
        if out.output_type == "grid" and hasattr(out.data, "shape"):
            arr = np.asarray(out.data)
            b64 = numpy_to_png_base64(arr)
            item["image"] = "data:image/png;base64," + b64
        elif out.output_type == "shader" and isinstance(out.data, str):
            item["shader"] = out.data
        rep = get_current_representation()
        glsl = rep.compile_to_shader(ind)
        if glsl:
            item["shader"] = glsl
        extra = getattr(rep, "serialize_individual_extra", lambda i: {})(ind)
        item.update(extra)
        results.append(item)
    rep = get_current_representation()
    return jsonify(
        {
            "results": results,
            "output_type": rep.output_type,
            "representation_id": rep.id,
        }
    )


@stateless_bp.route("/api/time-output", methods=["POST"])
@api_try_except
def api_time_output():
    """
    Stateless: query time/signal output for an individual with given inputs
    (debug panel).
    Body: { "individual": <representation-specific JSON>, <signal_id>: value ... }.
    Returns: { "timeOutput": float, "inputs": { <id>: value ... } }.
    """
    ind, _, _, err = _require_individual_from_request("time_output")
    if err is not None:
        return err
    data = request.json or {}
    inputs = parse_time_inputs(data, bipolar=False)
    result = get_current_representation().query_time_output(ind, inputs)
    if result is None:
        return api_error("Time output not supported by this representation.", 501)
    return jsonify(result)


@stateless_bp.route("/api/network", methods=["POST"])
@api_try_except
def api_network():
    """
    Stateless: get network visualization data for an individual.
    Body: { "individual": <representation-specific JSON> }
    Returns: { "id": key, "nodes": [...], "connections": [...] }
    """
    ind, individual_id, _, err = _require_individual_from_request("network")
    if err is not None:
        return err
    result = get_current_representation().get_network_data(ind)
    if result is None:
        return api_error(
            "Network visualization not supported by this representation.", 501
        )
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
    Stateless: adjust a connection weight in an individual and return updated shader.
    Body: { "individual": {...}, "network": <from registry>, "source",
    "target", "weight" }
    Returns: { "status": "success", "shader": "...", "individual": {...} }
    """
    ind, _, _, err = _require_individual_from_request("adjust_weight")
    if err is not None:
        return err
    data = request.json or {}
    network_type = data.get("network")
    if network_type not in NETWORK_SIGNALS:
        return api_error("Invalid network type.", 400)
    source_node = data.get("source")
    target_node = data.get("target")
    new_weight = float(data.get("weight", 0))
    result = get_current_representation().adjust_weight(
        ind, network_type, source_node, target_node, new_weight
    )
    if result is None:
        return api_error("Connection not found or invalid node ID.", 404)
    return jsonify(
        {
            "status": "success",
            "shader": result["shader"],
            "individual": result.get("individual", result.get("genome")),
            "network": network_type,
            "source": source_node,
            "target": target_node,
            "weight": new_weight,
        }
    )

"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state.
Blueprint is registered in server; engine and compiler are injected via
init_stateless_api. Endpoints: /api/compile, /api/random, /api/evaluate,
/api/time-output, /api/network, /api/adjust-weight.
"""

import base64
import io

import numpy as np
from flask import Blueprint, jsonify, request

from ..algorithm import DEFAULT_POPULATION_SIZE, MAX_POPULATION_SIZE
from ..genome import (
    DualGenome,
    dual_genome_from_json,
    dual_genome_to_json,
    extract_network_data,
    parse_network_node_id,
)
from ..glsl import ShaderCompiler
from ..signals import TIME_INPUTS
from .api_helpers import ERR_GENOME_REQUIRED, ERR_GENOMES_ARRAY_REQUIRED, api_error
from .response_builder import build_shader_response

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
    population limits). GET /api/config → substrate_id, output_type,
    population_size, max_population_size.
    """
    if _substrate is None:
        return api_error("No substrate configured.", 503)
    return jsonify(
        {
            "substrate_id": _substrate.id,
            "output_type": _substrate.output_type,
            "population_size": DEFAULT_POPULATION_SIZE,
            "max_population_size": MAX_POPULATION_SIZE,
        }
    )


def _require_engine():
    """Error if substrate has no engine (dual_cppn only)."""
    if _engine is None:
        return api_error(
            "This endpoint requires the dual_cppn substrate. "
            "Use a different EXPERIMENT_CONFIG or substrate in experiments.json.",
            501,
        )
    return None


def _shader_response_for_dual(
    dual_genome: DualGenome,
    individual_id: int,
    clicks: int = 0,
    compiler=None,
):
    """Build shader response dict for a dual genome; used by the compile endpoint."""
    comp = compiler if compiler is not None else _compiler
    return build_shader_response(
        dual_genome,
        individual_id=individual_id,
        clicks=clicks,
        compiler=comp,
        visual_config=_engine.config,
        time_config=_engine.time_config,
    )


def _require_can_compile():
    """Error if substrate cannot compile genomes to shaders (no compile_to_shader)."""
    if _engine is not None:
        return None
    compile_to_shader = getattr(_substrate, "compile_to_shader", None)
    if not callable(compile_to_shader):
        return api_error(
            "This endpoint requires a substrate that implements compile_to_shader. "
            "Use dual_cppn, single_cppn, or ca (or add compile_to_shader to your "
            "substrate).",
            501,
        )
    return None


@stateless_bp.route("/api/compile", methods=["POST"])
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
    try:
        data = request.json or {}
        genomes_data = data.get("genomes", [])
        if not genomes_data:
            return api_error(ERR_GENOMES_ARRAY_REQUIRED, 400)
        color_mode = (data.get("color_mode") or "").strip().lower()
        if color_mode and color_mode not in ("hsv", "rgb"):
            color_mode = "hsv"
        use_engine_compiler = _compiler and (
            not color_mode or color_mode == _compiler.color_mode
        )
        compiler = (
            _compiler
            if use_engine_compiler
            else (ShaderCompiler(color_mode=color_mode) if color_mode else None)
        )
        shaders = []
        if _engine is not None:
            comp = compiler or _compiler
            for i, g_data in enumerate(genomes_data):
                dual = dual_genome_from_json(
                    g_data, _engine.config, _engine.time_config
                )
                individual_id = g_data.get("key", dual.key if dual else i)
                clicks = g_data.get("clicks", 0)
                shaders.append(
                    _shader_response_for_dual(
                        dual, individual_id, clicks, compiler=comp
                    )
                )
        else:
            for i, g_data in enumerate(genomes_data):
                ind = _substrate.from_json(g_data)
                individual_id = g_data.get("key", getattr(ind, "key", i))
                clicks = g_data.get("clicks", 0)
                need_new_compiler = (
                    color_mode
                    and hasattr(_substrate, "config")
                    and _compiler
                    and color_mode != _compiler.color_mode
                )
                if need_new_compiler:
                    glsl = ShaderCompiler(color_mode=color_mode).compile_to_glsl(
                        ind, _substrate.config
                    )
                else:
                    glsl = _substrate.compile_to_shader(ind)
                num_nodes = (
                    len(getattr(ind, "nodes", {})) if hasattr(ind, "nodes") else 0
                )
                num_conn = (
                    len(getattr(ind, "connections", {}))
                    if hasattr(ind, "connections")
                    else 0
                )
                shaders.append(
                    {
                        "id": individual_id,
                        "shader": glsl or "",
                        "clicks": clicks,
                        "nodes": num_nodes,
                        "connections": num_conn,
                    }
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
    Returns: { "genomes": [ ... ], "output_type": "shader"|"grid"|... }
    Genome shape depends on substrate (dual_cppn: visual/time_signal; ca: rule, key).
    """
    try:
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
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    """
    Evaluate genomes with the current substrate and return displayable output.

    Body: { "genomes": [ ... ] } (each item is substrate-specific genome JSON).
    Returns: { "results": [ { "id", "output_type", "image"?, "shader"? } ],
        "output_type" }. Grid has "image"; shader has "shader".
    """
    try:
        data = request.json or {}
        genomes_data = data.get("genomes", [])
        if not genomes_data:
            return api_error(ERR_GENOMES_ARRAY_REQUIRED, 400)
        results = []
        for i, g_data in enumerate(genomes_data):
            ind = _substrate.from_json(g_data)
            individual_id = g_data.get("key", getattr(ind, "key", i))
            out = _substrate.evaluate(ind, {})
            item = {"id": individual_id, "output_type": out.output_type}
            if out.output_type == "grid" and hasattr(out.data, "shape"):
                from PIL import Image

                arr = np.asarray(out.data)
                if arr.dtype != np.uint8:
                    arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
                if arr.ndim == 2:
                    arr = np.stack([arr, arr, arr], axis=-1)
                pil = Image.fromarray(arr)
                buf = io.BytesIO()
                pil.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
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
    except Exception as e:
        return api_error(str(e), 500)


@stateless_bp.route("/api/time-output", methods=["POST"])
def api_time_output():
    """
    Stateless: query the Time CPPN for a genome with given inputs (for debug panel).
    Body: { "genome": { ... }, <id>: value ... } (0-1) for each time CPPN
    input; keys from signals TIME_INPUTS (e.g. raw_time, mouse_speed).
    Returns: { "timeOutput": float, "inputs": { <id>: value ... } }.
    """
    err = _require_engine()
    if err is not None:
        return err
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error(ERR_GENOME_REQUIRED, 400)
        dual = dual_genome_from_json(genome_data, _engine.config, _engine.time_config)
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
        return jsonify(
            {
                "timeOutput": time_output,
                "inputs": response_inputs,
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
    err = _require_engine()
    if err is not None:
        return err
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error(ERR_GENOME_REQUIRED, 400)

        dual = dual_genome_from_json(genome_data, _engine.config, _engine.time_config)
        individual_id = genome_data.get("key", dual.key if dual else 0)

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
    err = _require_engine()
    if err is not None:
        return err
    try:
        data = request.json or {}
        genome_data = data.get("genome")
        if not genome_data:
            return api_error(ERR_GENOME_REQUIRED, 400)

        network_type = data.get("network")  # 'visual' or 'time'
        source_node = data.get("source")
        target_node = data.get("target")
        new_weight = float(data.get("weight", 0))

        # Parse the genome
        dual = dual_genome_from_json(genome_data, _engine.config, _engine.time_config)

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
            return api_error(
                f"Invalid node ID format: {source_node} or {target_node}", 400
            )

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
        else:
            return api_error(
                f"Connection not found: {conn_key} ({source_node} -> {target_node})",
                404,
            )

    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error(str(e), 500)

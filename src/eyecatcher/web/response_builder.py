"""
Build shader + stats response dict for compile, save, and export.

Single source for the common shape so API and file bundles stay consistent.
Extend via extra_metadata or optional kwargs for research (e.g. compile_version).
"""

from __future__ import annotations

from typing import Any

import neat

from ..evaluation import dual_genome_network_stats
from ..genome import DualGenome
from ..glsl import ShaderCompiler


def build_shader_response(
    dual_genome: DualGenome,
    *,
    individual_id: int,
    clicks: int = 0,
    compiler: ShaderCompiler,
    visual_config: neat.Config,
    time_config: neat.Config,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the common shader + stats dict used by compile, save, and export.

    Returns dict with: id, shader, clicks, nodes, connections,
    visual_nodes, visual_connections, time_nodes, time_connections.
    If extra_metadata is provided, those keys are merged into the result
    (e.g. for save bundle metadata).
    """
    shader_code = compiler.compile_dual_to_glsl(dual_genome, visual_config, time_config)
    stats = dual_genome_network_stats(dual_genome)
    nodes = stats["visual_nodes"] + stats["time_nodes"]
    connections = stats["visual_connections"] + stats["time_connections"]

    out: dict[str, Any] = {
        "id": individual_id,
        "shader": shader_code,
        "clicks": clicks,
        "nodes": nodes,
        "connections": connections,
        "visual_nodes": stats["visual_nodes"],
        "visual_connections": stats["visual_connections"],
        "time_nodes": stats["time_nodes"],
        "time_connections": stats["time_connections"],
    }
    if extra_metadata:
        out.update(extra_metadata)
    return out

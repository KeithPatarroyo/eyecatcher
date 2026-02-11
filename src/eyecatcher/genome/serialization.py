"""
Genome serialization for stateless API and client storage.

JSON serialization/deserialization for NEAT genomes and DualGenomes,
plus deep copy. Network graph/stats for UI and API live in evaluation.network_data.
"""

from typing import Any, Optional

import neat

from .genome import DualGenome


def genome_to_json(genome: neat.DefaultGenome) -> dict[str, Any]:
    """Serialize a NEAT DefaultGenome to a JSON-serializable dict."""
    nodes = {}
    for node_id, node in genome.nodes.items():
        nodes[str(node_id)] = {
            "bias": float(getattr(node, "bias", 0.0)),
            "response": float(getattr(node, "response", 1.0)),
            "activation": str(getattr(node, "activation", "sigmoid")),
            "aggregation": str(getattr(node, "aggregation", "sum")),
        }
    connections = {}
    for key, conn in genome.connections.items():
        conn_key = f"{key[0]}_{key[1]}"
        connections[conn_key] = {
            "innovation": int(getattr(conn, "innovation", 0)),
            "weight": float(getattr(conn, "weight", 0.0)),
            "enabled": bool(getattr(conn, "enabled", True)),
        }
    return {
        "key": genome.key if genome.key is not None else 0,
        "fitness": genome.fitness,
        "nodes": nodes,
        "connections": connections,
    }


def genome_from_json(
    data: dict[str, Any], visual_config: neat.Config
) -> neat.DefaultGenome:
    """Deserialize a NEAT DefaultGenome from a dict (e.g. from JSON)."""
    genome_config = visual_config.genome_config
    genome = neat.DefaultGenome(data.get("key", 0))
    genome.fitness = data.get("fitness")
    genome.nodes = {}
    genome.connections = {}

    for nid_str, node_data in data.get("nodes", {}).items():
        nid = int(nid_str)
        node = genome_config.node_gene_type(nid)
        node.bias = float(node_data.get("bias", 0.0))
        node.response = float(node_data.get("response", 1.0))
        act = str(node_data.get("activation", "sigmoid")).strip()
        node.activation = act if act else "sigmoid"
        node.aggregation = str(node_data.get("aggregation", "sum"))
        genome.nodes[nid] = node

    for conn_key_str, conn_data in data.get("connections", {}).items():
        parts = conn_key_str.split("_", 1)
        if len(parts) != 2:
            continue
        try:
            in_id, out_id = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        key = (in_id, out_id)
        innovation = conn_data.get("innovation")
        if innovation is None:
            innovation = abs(hash(key)) % (2**31)
        else:
            innovation = int(innovation)
        conn = genome_config.connection_gene_type(key, innovation=innovation)
        conn.weight = float(conn_data.get("weight", 0.0))
        conn.enabled = bool(conn_data.get("enabled", True))
        genome.connections[key] = conn
    return genome


def dual_genome_to_json(dual: DualGenome) -> dict[str, Any]:
    """
    Serialize a DualGenome to a JSON-serializable dict.

    Args:
        dual: The dual genome to serialize.

    Returns:
        Dict with "key", "visual", "time_signal" suitable for JSON.
    """
    return {
        "key": dual.key,
        "visual": genome_to_json(dual.visual),
        "time_signal": genome_to_json(dual.time_signal),
    }


def dual_genome_from_json(
    data: dict[str, Any],
    visual_config: neat.Config,
    time_config: neat.Config,
) -> DualGenome:
    """
    Deserialize a DualGenome from a dict (e.g. from JSON).

    Args:
        data: Dict with "visual" and "time_signal" genome dicts.
        visual_config: NEAT config for the visual genome.
        time_config: NEAT config for the time_signal genome.

    Returns:
        Reconstructed DualGenome.
    """
    visual_data = data.get("visual", {})
    time_data = data.get("time_signal", {})
    if not visual_data or not time_data:
        raise ValueError("dual genome JSON must contain 'visual' and 'time_signal'")

    visual = genome_from_json(visual_data, visual_config)
    time_signal = genome_from_json(time_data, time_config)
    _update_node_indexer_from_genome(visual, visual_config.genome_config)
    _update_node_indexer_from_genome(time_signal, time_config.genome_config)

    key = data.get("key", 0)
    return DualGenome(visual=visual, time_signal=time_signal, key=key)


def _update_node_indexer_from_genome(
    genome: neat.DefaultGenome, genome_config: Any
) -> None:
    """Update the genome config's node indexer to prevent ID collisions."""
    if not genome.nodes:
        return
    hidden_node_ids = [
        nid for nid in genome.nodes.keys() if nid >= genome_config.num_outputs
    ]
    if not hidden_node_ids:
        return
    max_node_id = max(hidden_node_ids)
    if hasattr(genome_config, "node_indexer"):
        import itertools

        genome_config.node_indexer = itertools.count(max_node_id + 1)


def copy_genome(
    genome: neat.DefaultGenome, visual_config: neat.Config
) -> neat.DefaultGenome:
    """Create a deep copy of a genome by serializing and deserializing."""
    return genome_from_json(genome_to_json(genome), visual_config)


def copy_dual_genome(
    dual: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    new_key: Optional[int] = None,
) -> DualGenome:
    """Create a deep copy of a dual genome."""
    return DualGenome(
        visual=copy_genome(dual.visual, visual_config),
        time_signal=copy_genome(dual.time_signal, time_config),
        key=new_key if new_key is not None else dual.key,
    )

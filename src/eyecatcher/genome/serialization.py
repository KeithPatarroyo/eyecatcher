"""
Genome serialization for stateless API and client storage.

JSON serialization/deserialization for NEAT genomes, plus deep copy.
DualGenome serialization lives in substrate.dual_genome.
"""

from typing import Any

import neat


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
    data: dict[str, Any], neat_config: neat.Config
) -> neat.DefaultGenome:
    """Deserialize a NEAT DefaultGenome from a dict (e.g. from JSON)."""
    genome_config = neat_config.genome_config
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
    genome: neat.DefaultGenome, neat_config: neat.Config
) -> neat.DefaultGenome:
    """Create a deep copy of a genome by serializing and deserializing."""
    return genome_from_json(genome_to_json(genome), neat_config)

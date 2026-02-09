"""
Genome serialization utilities for stateless API and client storage.

Provides JSON serialization/deserialization for NEAT genomes and DualGenomes,
plus deep copy utilities.
"""

from typing import TYPE_CHECKING, Any

import neat

if TYPE_CHECKING:
    from .cppn_engine import CPPNEngine, DualGenome


def genome_to_json(genome: neat.DefaultGenome) -> dict[str, Any]:
    """
    Serialize a NEAT DefaultGenome to a JSON-serializable dict.
    """
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


def genome_from_json(data: dict[str, Any], config: neat.Config) -> neat.DefaultGenome:
    """
    Deserialize a NEAT DefaultGenome from a dict (e.g. from JSON).
    Uses the given config's genome_config for gene types.
    """
    gc = config.genome_config
    genome = neat.DefaultGenome(data.get("key", 0))
    genome.fitness = data.get("fitness")
    genome.nodes = {}
    genome.connections = {}

    for nid_str, nd in data.get("nodes", {}).items():
        nid = int(nid_str)
        node = gc.node_gene_type(nid)
        node.bias = float(nd.get("bias", 0.0))
        node.response = float(nd.get("response", 1.0))
        node.activation = str(nd.get("activation", "sigmoid"))
        node.aggregation = str(nd.get("aggregation", "sum"))
        genome.nodes[nid] = node

    for conn_key_str, cd in data.get("connections", {}).items():
        parts = conn_key_str.split("_", 1)
        if len(parts) != 2:
            continue
        try:
            in_id, out_id = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        key = (in_id, out_id)
        # NEAT-python requires innovation number for DefaultConnectionGene
        innovation = cd.get("innovation")
        if innovation is None:
            # Synthetic innovation when loading JSON that omitted it (e.g. legacy or imported genomes)
            innovation = abs(hash(key)) % (2**31)
        else:
            innovation = int(innovation)
        conn = gc.connection_gene_type(key, innovation=innovation)
        conn.weight = float(cd.get("weight", 0.0))
        conn.enabled = bool(cd.get("enabled", True))
        genome.connections[key] = conn
    return genome


def dual_genome_to_json(dual: "DualGenome") -> dict[str, Any]:
    """Serialize a DualGenome to a JSON-serializable dict."""
    return {
        "key": dual.key,
        "visual": genome_to_json(dual.visual),
        "time_signal": genome_to_json(dual.time_signal),
    }


def dual_genome_from_json(data: dict[str, Any], engine: "CPPNEngine") -> "DualGenome":
    """Deserialize a DualGenome from a dict (e.g. from JSON)."""
    # Import here to avoid circular dependency
    from .cppn_engine import DualGenome

    visual_data = data.get("visual", {})
    time_data = data.get("time_signal", {})
    if not visual_data or not time_data:
        raise ValueError("dual genome JSON must contain 'visual' and 'time_signal'")

    # Deserialize both genomes
    visual = genome_from_json(visual_data, engine.config)
    time_signal = genome_from_json(time_data, engine.time_config)

    # Additional safety: update node indexers globally to prevent collisions
    # This is especially important when loading from genealogy
    _update_node_indexer_from_genome(visual, engine.config.genome_config)
    _update_node_indexer_from_genome(time_signal, engine.time_config.genome_config)

    key = data.get("key", 0)
    return DualGenome(visual=visual, time_signal=time_signal, key=key)


def _update_node_indexer_from_genome(
    genome: "neat.DefaultGenome", genome_config: "neat.DefaultGenomeConfig"
):
    """Update the genome config's node indexer to prevent ID collisions."""
    if not genome.nodes:
        return

    # Find the maximum node ID in this genome (only hidden nodes, which have positive IDs)
    # Input nodes have negative IDs, output nodes are 0+, hidden nodes are higher
    hidden_node_ids = [
        nid for nid in genome.nodes.keys() if nid >= genome_config.num_outputs
    ]

    if not hidden_node_ids:
        # No hidden nodes yet, nothing to update
        return

    max_node_id = max(hidden_node_ids)

    # Update the indexer by replacing it with a new counter starting at max_node_id + 1
    # This prevents ID collisions when mutating loaded genomes
    if hasattr(genome_config, "node_indexer"):
        import itertools

        # Replace the counter to start at max_node_id + 1
        genome_config.node_indexer = itertools.count(max_node_id + 1)


def copy_genome(genome: neat.DefaultGenome, config: neat.Config) -> neat.DefaultGenome:
    """Create a deep copy of a genome by serializing and deserializing."""
    return genome_from_json(genome_to_json(genome), config)


def copy_dual_genome(
    dual: "DualGenome", engine: "CPPNEngine", new_key: int = None
) -> "DualGenome":
    """Create a deep copy of a dual genome."""
    # Import here to avoid circular dependency
    from .cppn_engine import DualGenome

    return DualGenome(
        visual=copy_genome(dual.visual, engine.config),
        time_signal=copy_genome(dual.time_signal, engine.time_config),
        key=new_key if new_key is not None else dual.key,
    )

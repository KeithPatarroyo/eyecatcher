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
        act = str(nd.get("activation", "sigmoid")).strip()
        node.activation = act if act else "sigmoid"
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
            # Synthetic innovation when JSON omitted it (e.g. legacy or imported)
            innovation = abs(hash(key)) % (2**31)
        else:
            innovation = int(innovation)
        conn = gc.connection_gene_type(key, innovation=innovation)
        conn.weight = float(cd.get("weight", 0.0))
        conn.enabled = bool(cd.get("enabled", True))
        genome.connections[key] = conn
    return genome


def dual_genome_network_stats(dual: "DualGenome") -> dict[str, int]:
    """
    Return node and enabled-connection counts for both genomes.

    Returns:
        Dict with visual_nodes, visual_connections, time_nodes, time_connections.
    """
    v_nodes = len(dual.visual.nodes)
    v_conns = len([c for c in dual.visual.connections.values() if c.enabled])
    t_nodes = len(dual.time_signal.nodes)
    t_conns = len([c for c in dual.time_signal.connections.values() if c.enabled])
    return {
        "visual_nodes": v_nodes,
        "visual_connections": v_conns,
        "time_nodes": t_nodes,
        "time_connections": t_conns,
    }


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
    # Important when loading from genealogy
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

    # Find max node ID (hidden nodes have positive IDs)
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


def extract_network_data(
    genome: neat.DefaultGenome, network_type: str, config: neat.Config
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract nodes and connections from a genome for network visualization.

    Returns (nodes, connections) as lists of dicts with id, label, type, etc.
    """
    nodes = []
    node_id_map = {}

    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs

    x_offset = 1000 if network_type == "time" else 0

    if network_type == "time":
        input_labels = [
            "raw_time",
            "mouse_speed",
            "mouse_distance",
            "inactivity",
            "bias",
        ]
    else:
        input_labels = [
            "x",
            "y",
            "distance",
            "time",
            "mouse_speed",
            "mouse_distance",
            "inactivity",
            "bias",
        ]

    for i in range(num_inputs):
        neat_id = -(i + 1)
        vis_id = f"{network_type}_input_{neat_id}"
        node_id_map[neat_id] = vis_id
        label = input_labels[i] if i < len(input_labels) else f"Input {i}"
        nodes.append(
            {
                "id": vis_id,
                "label": label,
                "type": "input",
                "network": network_type,
                "index": i,
                "x": -400 + x_offset,
                "y": (i - num_inputs / 2) * 80,
            }
        )

    hidden_list = sorted(genome.nodes.keys())
    for idx, neat_id in enumerate(hidden_list):
        node = genome.nodes[neat_id]
        vis_id = f"{network_type}_hidden_{neat_id}"
        node_id_map[neat_id] = vis_id
        nodes.append(
            {
                "id": vis_id,
                "label": f"Node {neat_id}",
                "type": "hidden",
                "network": network_type,
                "activation": node.activation,
                "bias": float(node.bias),
                "index": neat_id,
                "x": 0 + x_offset,
                "y": (idx - len(hidden_list) / 2) * 80,
            }
        )

    if network_type == "time":
        output_labels = ["output"]
    else:
        output_labels = ["red", "green", "blue"]

    for i in range(num_outputs):
        neat_id = i
        vis_id = f"{network_type}_output_{neat_id}"
        node_id_map[neat_id] = vis_id
        label = output_labels[i] if i < len(output_labels) else f"Output {i}"
        nodes.append(
            {
                "id": vis_id,
                "label": label,
                "type": "output",
                "network": network_type,
                "index": i,
                "x": 400 + x_offset,
                "y": (i - num_outputs / 2) * 80,
            }
        )

    connections = []
    for conn_id, conn in genome.connections.items():
        if conn.enabled:
            input_node, output_node = conn_id
            source_id = node_id_map.get(input_node, str(input_node))
            target_id = node_id_map.get(output_node, str(output_node))
            connections.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "weight": float(conn.weight),
                    "network": network_type,
                }
            )

    return nodes, connections

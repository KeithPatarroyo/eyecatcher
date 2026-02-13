"""
Network graph extraction for UI and API.

Produces node/connection lists from genomes for visualization.
Used by substrate get_network_data, genome_visualizer.
"""

from typing import Any, Optional

import neat

from ..signals.signals import (
    NETWORK_SIGNALS,
    input_labels,
    output_labels,
)


def _append_nodes_for_layer(
    nodes: list[dict[str, Any]],
    node_id_map: dict[int, str],
    network_type: str,
    layer_type: str,
    id_label_list: list[tuple[int, str]],
    x_pos: float,
    extra_per_node: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Append one layer of nodes (input, hidden, or output) with vertical spacing."""
    n = len(id_label_list)
    y_positions = [(i - n / 2) * 80 for i in range(n)]
    extras = extra_per_node if extra_per_node is not None else [{} for _ in range(n)]
    for i, ((neat_id, label), extra) in enumerate(zip(id_label_list, extras)):
        vis_id = f"{network_type}_{layer_type}_{neat_id}"
        node_id_map[neat_id] = vis_id
        nodes.append(
            {
                "id": vis_id,
                "label": label,
                "type": layer_type,
                "network": network_type,
                "index": neat_id if layer_type == "hidden" else i,
                "x": x_pos,
                "y": y_positions[i],
                **extra,
            }
        )


def extract_network_data(
    genome: neat.DefaultGenome,
    network_type: str,
    neat_config: neat.Config,
    x_offset: float = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract nodes and connections from a genome for network visualization.

    Args:
        genome: NEAT DefaultGenome for any network type.
        network_type: Key for NETWORK_SIGNALS (e.g. "visual", "time").
        neat_config: NEAT config for this genome.
        x_offset: X offset for layout (e.g. 0 for first network, 1000 for second).

    Returns:
        (nodes, connections) as lists of dicts with id, label, type, etc.
    """
    nodes = []
    node_id_map = {}
    num_inputs = neat_config.genome_config.num_inputs
    num_outputs = neat_config.genome_config.num_outputs
    signals, outputs = NETWORK_SIGNALS[network_type]
    input_label_list = input_labels(signals)
    input_list = [
        (-(i + 1), input_label_list[i] if i < len(input_label_list) else f"Input {i}")
        for i in range(num_inputs)
    ]
    _append_nodes_for_layer(
        nodes,
        node_id_map,
        network_type,
        "input",
        input_list,
        -400 + x_offset,
    )

    hidden_list = sorted(genome.nodes.keys())
    hidden_id_labels = [(nid, f"Node {nid}") for nid in hidden_list]
    hidden_extras = [
        {
            "activation": genome.nodes[nid].activation,
            "bias": float(genome.nodes[nid].bias),
        }
        for nid in hidden_list
    ]
    _append_nodes_for_layer(
        nodes,
        node_id_map,
        network_type,
        "hidden",
        hidden_id_labels,
        0 + x_offset,
        hidden_extras,
    )

    output_label_list = output_labels(outputs)
    output_list = [
        (i, output_label_list[i] if i < len(output_label_list) else f"Output {i}")
        for i in range(num_outputs)
    ]
    _append_nodes_for_layer(
        nodes,
        node_id_map,
        network_type,
        "output",
        output_list,
        400 + x_offset,
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


def parse_network_node_id(node_id_str: str) -> int:
    """
    Parse a frontend node ID string back to the numeric NEAT node ID.

    Args:
        node_id_str: String like "visual_input_-1" or "time_hidden_5".

    Returns:
        The integer node ID.

    Raises:
        ValueError: If the format is invalid.
    """
    parts = node_id_str.split("_")
    if len(parts) >= 3:
        return int(parts[-1])
    return int(node_id_str)

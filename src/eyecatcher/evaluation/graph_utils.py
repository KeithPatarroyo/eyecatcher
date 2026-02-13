"""
Graph algorithms for NEAT genomes: layer assignment and output-reachable nodes.

Used by genome_visualizer for layout and active-node highlighting.
Reusable for any NEAT DefaultGenome (visual, time, or other).
"""

import neat


def assign_layers(
    genome: neat.DefaultGenome,
    input_ids: list[int],
    output_ids: list[int],
) -> dict[int, int]:
    """
    Assign hidden nodes to layers (0-based) by BFS from inputs.
    Returns dict node_id -> layer for hidden nodes only.
    """
    connections = [
        (c.key[0], c.key[1]) for c in genome.connections.values() if c.enabled
    ]
    adjacency: dict[int, list[int]] = {}
    for src, dst in connections:
        adjacency.setdefault(src, []).append(dst)

    layers: dict[int, int] = {}
    visited: set[int] = set()
    queue: list[tuple[int, int]] = [(n, 0) for n in input_ids]

    while queue:
        node_id, layer = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        if node_id not in input_ids and node_id not in output_ids:
            layers[node_id] = layer
        for neighbor in adjacency.get(node_id, []):
            if neighbor not in visited:
                queue.append((neighbor, layer + 1))

    if layers:
        min_layer = min(layers.values())
        layers = {k: v - min_layer for k, v in layers.items()}
    return layers


def get_nodes_required_for_output(
    genome: neat.DefaultGenome,
    num_outputs: int,
) -> set[int]:
    """
    Backward BFS from outputs; returns set of node IDs that contribute to output.
    """
    output_ids = list(range(num_outputs))
    reverse_adjacency: dict[int, list[int]] = {}
    for conn in genome.connections.values():
        if conn.enabled:
            src, dst = conn.key
            reverse_adjacency.setdefault(dst, []).append(src)

    required: set[int] = set(output_ids)
    queue: list[int] = list(output_ids)
    visited: set[int] = set()

    while queue:
        node_id = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        for src in reverse_adjacency.get(node_id, []):
            required.add(src)
            if src not in visited:
                queue.append(src)
    return required

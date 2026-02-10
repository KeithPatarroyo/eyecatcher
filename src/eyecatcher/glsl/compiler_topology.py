"""
Topology helpers for shader compilation: enabled connections and evaluation order.

Used by ShaderCompiler and NodeCodeGenerator. Researchers changing network structure
(e.g. recurrent connections) would touch this module; standard feedforward CPPN
does not require changes.
"""

import neat


def get_enabled_connections(genome: neat.DefaultGenome) -> list[tuple[int, int, float]]:
    """Return (src_id, dst_id, weight) for all enabled connections."""
    return [
        (c.key[0], c.key[1], c.weight) for c in genome.connections.values() if c.enabled
    ]


def topological_sort(
    genome: neat.DefaultGenome,
    connections: list[tuple[int, int, float]],
    config: neat.Config,
) -> list[int]:
    """
    Return node IDs in evaluation order (inputs first, then hidden, then outputs).
    Uses Kahn's algorithm. Depends on config for num_inputs and num_outputs.
    """
    in_degree: dict[int, int] = {}
    adjacency: dict[int, list[int]] = {}
    all_nodes: set[int] = set()

    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    input_nodes = list(range(-num_inputs, 0))
    output_nodes = list(range(num_outputs))

    all_nodes.update(input_nodes)
    all_nodes.update(output_nodes)
    all_nodes.update(genome.nodes.keys())

    for node in all_nodes:
        in_degree[node] = 0
        adjacency[node] = []

    for src, dst, _ in connections:
        adjacency[src].append(dst)
        in_degree[dst] += 1
        all_nodes.add(src)
        all_nodes.add(dst)

    queue = [node for node in all_nodes if in_degree[node] == 0]
    sorted_nodes: list[int] = []

    while queue:
        node = queue.pop(0)
        sorted_nodes.append(node)
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return sorted_nodes

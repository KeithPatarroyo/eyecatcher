"""
Representation-specific receptor subclasses.

NeatReceptor binds signals to a NEAT network (config, query, visualization).
For grid representations (e.g. CA), use the base Receptor from signals.receptor
with interaction inputs (e.g. mouse_x, mouse_y); no grid-specific subclass needed.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

import neat

from .. import get_root_dir
from ..genome.operators import register_custom_activations
from ..glsl.input_map import build_glsl_input_map
from ..inspection.network_data import extract_network_data as _extract_network_data
from ..signals.receptor import Receptor
from ..signals.sensory_system import Output, Signal
from ..signals.validation import validate_neat_config

# ---------------------------------------------------------------------------
# NetworkContribution: opaque output from compiling a genome through a receptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NetworkContribution:
    """Opaque topology and node data from compiling a genome through a receptor.

    Used by the rule assembler to generate rendering code. No GLSL in the domain.
    """

    connections: tuple[tuple[int, int, float], ...]  # (src_id, dst_id, weight)
    node_order: tuple[int, ...]  # topological order
    node_data: dict[
        int, tuple[str, float, float]
    ]  # node_id -> (activation, bias, response)
    input_map: dict[int, str]  # NEAT node ID -> variable name (e.g. -1 -> "v_x")
    num_inputs: int
    num_outputs: int
    prefix: str = ""  # e.g. "time_" for time network


def _get_enabled_connections(
    genome: neat.DefaultGenome,
) -> list[tuple[int, int, float]]:
    """Return (src_id, dst_id, weight) for all enabled connections."""
    return [
        (c.key[0], c.key[1], c.weight) for c in genome.connections.values() if c.enabled
    ]


def _topological_sort(
    genome: neat.DefaultGenome,
    connections: list[tuple[int, int, float]],
    config: neat.Config,
) -> list[int]:
    """Return node IDs in evaluation order (inputs first, then hidden, then outputs)."""
    in_degree: dict[int, int] = {}
    adjacency: dict[int, list[int]] = {}
    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    input_nodes = list(range(-num_inputs, 0))
    output_nodes = list(range(num_outputs))
    all_nodes: set[int] = set()
    all_nodes.update(input_nodes)
    all_nodes.update(output_nodes)
    all_nodes.update(genome.nodes.keys())
    for src, dst, _ in connections:
        all_nodes.add(src)
        all_nodes.add(dst)
    for node in all_nodes:
        in_degree[node] = 0
        adjacency[node] = []
    for src, dst, _ in connections:
        adjacency[src].append(dst)
        in_degree[dst] += 1
    queue = [n for n in all_nodes if in_degree[n] == 0]
    sorted_nodes: list[int] = []
    while queue:
        node = queue.pop(0)
        sorted_nodes.append(node)
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return sorted_nodes


def _extract_node_data(
    genome: neat.DefaultGenome,
    node_order: list[int],
    num_outputs: int,
    input_map: dict[int, str],
) -> dict[int, tuple[str, float, float]]:
    """Extract (activation, bias, response) for each non-input node."""
    result: dict[int, tuple[str, float, float]] = {}
    for node_id in node_order:
        if node_id in input_map:
            continue
        if node_id in genome.nodes:
            node = genome.nodes[node_id]
            result[node_id] = (node.activation, node.bias, node.response)
        else:
            result[node_id] = ("identity", 0.0, 1.0)
    return result


# Cache NEAT config by resolved path so NeatReceptor can stay immutable.
_neat_config_cache: dict[str, neat.Config] = {}


def _load_neat_config(
    resolved_path: str,
    signals_in: list[Signal],
    signals_out: list[Output],
    label: str,
) -> neat.Config:
    """Load NEAT config; register activations; validate. Cached by resolved path."""
    if resolved_path not in _neat_config_cache:
        config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            resolved_path,
        )
        register_custom_activations(config)
        validate_neat_config(config, signals_in, list(signals_out), label)
        _neat_config_cache[resolved_path] = config
    return _neat_config_cache[resolved_path]


@dataclass(frozen=True)
class NeatReceptor(Receptor):
    """Receptor that binds signals to a NEAT CPPN network.

    Owns config path and lazy-loads NEAT config. Provides query(),
    glsl_input_map(), network_stats(), extract_network_data(), render_network_pdf().
    """

    config_path: str = ""

    @property
    def config(self) -> neat.Config:
        """Lazy-load and return NEAT config (cached by resolved path)."""
        root = Path(get_root_dir())
        resolved = Path(self.config_path)
        if not resolved.is_absolute():
            resolved = root / resolved
        return _load_neat_config(
            str(resolved),
            list(self.inputs),
            list(self.outputs),
            self.name,
        )

    def query(
        self, genome: neat.DefaultGenome, values: dict[str, float]
    ) -> list[float]:
        """Run network: apply derived inputs, return raw outputs."""
        in_arr = self.to_array(values)
        net = neat.nn.FeedForwardNetwork.create(genome, self.config)
        return net.activate(in_arr)

    def compile(self, genome: neat.DefaultGenome) -> NetworkContribution:
        """Compile genome through this receptor into an opaque network contribution.

        Extracts topology and node parameters only; no rendering code is generated here.
        """
        config = self.config
        connections = _get_enabled_connections(genome)
        node_order = _topological_sort(genome, connections, config)
        input_map = build_glsl_input_map(self.inputs)
        num_inputs = config.genome_config.num_inputs
        num_outputs = config.genome_config.num_outputs
        node_data = _extract_node_data(genome, node_order, num_outputs, input_map)
        prefix = "" if self.role == "primary" else f"{self.name}_"
        return NetworkContribution(
            connections=tuple(connections),
            node_order=tuple(node_order),
            node_data=node_data,
            input_map=input_map,
            num_inputs=num_inputs,
            num_outputs=num_outputs,
            prefix=prefix,
        )

    def glsl_input_map(self) -> dict[int, str]:
        """Map NEAT negative node IDs to GLSL var names for this receptor's inputs."""
        return build_glsl_input_map(self.inputs)

    def network_stats(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        """Return {name}_nodes and {name}_connections for this receptor.

        Expects NEAT-like genome shape: .nodes (dict), .connections (dict),
        each connection with .enabled. getattr used for NEAT library compatibility.
        """
        nodes = getattr(genome, "nodes", {}) or {}
        conns = getattr(genome, "connections", {}) or {}
        return {
            f"{self.name}_nodes": len(nodes),
            f"{self.name}_connections": sum(
                1 for c in conns.values() if getattr(c, "enabled", True)
            ),
        }

    def extract_network_data(
        self,
        genome: neat.DefaultGenome,
        x_offset: float = 0,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract nodes and connections for UI visualization."""
        return _extract_network_data(
            genome,
            self.inputs,
            self.outputs,
            self.config,
            x_offset=x_offset,
            network_type=self.name,
        )

    def render_network_pdf(
        self,
        genome: neat.DefaultGenome,
        output: str | BinaryIO,
    ) -> bytes | None:
        """Render genome network to PDF. Bytes if output is file-like else None."""
        from ..inspection.genome_visualizer import render_genome_network_pdf

        return render_genome_network_pdf(
            genome,
            self.config,
            output,
            signals_in=list(self.inputs),
            signals_out=list(self.outputs),
        )

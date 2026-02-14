"""
Representation-specific socket subclasses.

NeatSocket binds signals to a NEAT network (config, query, visualization).
GridSocket binds signals to a grid (e.g. CA cell coordinates).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, BinaryIO

import neat

from .. import get_root_dir
from ..genome.activation import register_custom_activations
from ..inspection.network_data import extract_network_data as _extract_network_data
from ..signals.socket import Socket
from ..signals.spec import Output, Signal, build_glsl_input_map
from ..signals.validation import validate_neat_config

# Cache NEAT config by resolved path so NeatSocket can stay immutable.
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
class NeatSocket(Socket):
    """Socket that binds signals to a NEAT CPPN network.

    Owns config path and lazy-loads NEAT config. Provides query(),
    glsl_input_map(), network_stats(), extract_network_data(), render_network_pdf().
    """

    config_path: str = ""

    @property
    def config(self) -> neat.Config:
        """Lazy-load and return NEAT config (cached by resolved path)."""
        root = get_root_dir()
        resolved = self.config_path
        if not os.path.isabs(resolved):
            resolved = os.path.join(root, resolved)
        return _load_neat_config(
            resolved,
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

    def glsl_input_map(self) -> dict[int, str]:
        """Map NEAT negative node IDs to GLSL var names for this socket's inputs."""
        return build_glsl_input_map(self.inputs)

    def network_stats(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        """Return {name}_nodes and {name}_connections for this socket.

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


@dataclass(frozen=True)
class GridSocket(Socket):
    """Socket that binds signals to grid cell coordinates.

    Used e.g. for CA interaction (mouse_x, mouse_y -> cell row, col).
    """

    grid_size: int = 0

    def map_to_cell(self, values: dict[str, float]) -> tuple[int, int]:
        """Map signal values (e.g. mouse_x, mouse_y in [0,1]) to grid (row, col)."""
        mx = values.get("mouse_x", 0.0)
        my = values.get("mouse_y", 0.0)
        col = int(mx * self.grid_size) % self.grid_size
        row = int(my * self.grid_size) % self.grid_size
        return row, col

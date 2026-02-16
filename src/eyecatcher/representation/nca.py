"""
Neural Cellular Automata (NCA) representation.

Mordvintsev-style per-cell update with Sobel perception, evolved via NEAT,
following CA-NEAT from Nichele (2017).
The NCA update rule is a NEAT network (14 inputs -> 4 state-delta outputs).
State: 4 channels (RGB + alpha). FBO ping-pong on the frontend; CPU simulation
for express() thumbnails.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import neat
import numpy as np

from ..genome.operators import crossover_genomes, mutate_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..glsl.nca_rule_assembler import assemble_nca_step_shader
from ..inspection.network_data import parse_network_node_id
from ..signals import catalog
from ..signals.receptor import Receptor
from ..signals.sensory_system import SensorySystem
from ._image_util import rgb_to_png_base64
from .base import RepresentationBase
from .mixins import GridAnalyzable, NetworkInspectable, Saveable
from .protocol import Behaviour, Phenotype, RepresentationOutput, Substrate
from .receptors import NeatReceptor

DEFAULT_GRID_SIZE = 64
DEFAULT_NCA_STEPS = 48


def _sobel_perception(state: np.ndarray) -> np.ndarray:
    """Compute 3x3 Sobel perception: (H, W, 4) -> (H, W, 12). state in [-1,1]."""
    grad_x = np.zeros_like(state)
    grad_y = np.zeros_like(state)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dc == -1:
                wx = -1.0 if dr != 0 else -2.0
            elif dc == 1:
                wx = 1.0 if dr != 0 else 2.0
            else:
                wx = 0.0
            if dr == -1:
                wy = -1.0 if dc != 0 else -2.0
            elif dr == 1:
                wy = 1.0 if dc != 0 else 2.0
            else:
                wy = 0.0
            rolled = np.roll(np.roll(state, dr, axis=0), dc, axis=1)
            grad_x += wx * rolled
            grad_y += wy * rolled
    return np.concatenate([state, grad_x, grad_y], axis=2)


def _nca_step_cpu_neat(
    state: np.ndarray,
    network: neat.nn.FeedForwardNetwork,
    receptor: NeatReceptor,
    signal_values: np.ndarray,
    step_index: int,
    grid_size: int,
) -> np.ndarray:
    """One NCA step on CPU using NEAT feedforward network."""
    h, w, _ = state.shape
    perc = _sobel_perception(state)
    rng = np.random.default_rng(step_index)
    mouse_x = float(signal_values[1]) if signal_values.size >= 2 else 0.5
    mouse_y = float(signal_values[2]) if signal_values.size >= 3 else 0.5
    raw_time = float(signal_values[0]) if signal_values.size >= 1 else 0.0

    new_state = np.zeros_like(state)
    for r in range(h):
        for c in range(w):
            cell_values = {
                "nca_self_r": float(perc[r, c, 0]),
                "nca_self_g": float(perc[r, c, 1]),
                "nca_self_b": float(perc[r, c, 2]),
                "nca_self_a": float(perc[r, c, 3]),
                "nca_dx_r": float(perc[r, c, 4]),
                "nca_dx_g": float(perc[r, c, 5]),
                "nca_dx_b": float(perc[r, c, 6]),
                "nca_dx_a": float(perc[r, c, 7]),
                "nca_dy_r": float(perc[r, c, 8]),
                "nca_dy_g": float(perc[r, c, 9]),
                "nca_dy_b": float(perc[r, c, 10]),
                "nca_dy_a": float(perc[r, c, 11]),
                "raw_time": raw_time,
                "mouse_cell_dist": float(
                    np.sqrt(
                        ((c + 0.5) / w - mouse_x) ** 2 + ((r + 0.5) / h - mouse_y) ** 2
                    )
                ),
            }
            inputs_arr = receptor.to_array(cell_values)
            ds = np.array(network.activate(inputs_arr), dtype=np.float64)
            if rng.random() < 0.5:
                ds *= 0.0
            new_state[r, c] = state[r, c] + ds

    alpha = state[:, :, 3:4]
    max_alpha = np.maximum(alpha, 0.0)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            shifted = np.roll(np.roll(alpha, dr, axis=0), dc, axis=1)
            max_alpha = np.maximum(max_alpha, shifted)
    alive = (max_alpha > 0.1).astype(np.float64)
    new_state = new_state * alive
    return np.clip(new_state, -1.0, 1.0)


def _run_nca_cpu_neat(
    seed: np.ndarray,
    genome: neat.DefaultGenome,
    receptor: NeatReceptor,
    steps: int,
    signal_values: np.ndarray,
) -> np.ndarray:
    """Run NCA for steps using NEAT network; return final state (H, W, 4)."""
    config = receptor.config
    network = neat.nn.FeedForwardNetwork.create(genome, config)
    state = np.asarray(seed, dtype=np.float64).copy()
    h, w = state.shape[:2]
    for step in range(steps):
        state = _nca_step_cpu_neat(state, network, receptor, signal_values, step, w)
    return state


def _state_to_rgb(state: np.ndarray) -> np.ndarray:
    """Convert (H, W, 4) state to (H, W, 3) uint8 RGB; alpha > 0.1 = visible."""
    rgb = (np.clip(state[:, :, :3] * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)
    alive = (state[:, :, 3] > 0.1)[:, :, np.newaxis]
    rgb = rgb * alive
    return rgb


def _create_seed(grid_size: int) -> np.ndarray:
    """Fixed center-pixel seed (not part of genome)."""
    seed = np.zeros((grid_size, grid_size, 4), dtype=np.float64)
    mid = grid_size // 2
    seed[mid, mid, 3] = 1.0
    return seed


_NCA_DISPLAY_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
in vec2 vUV;
out vec4 fragColor;
void main() {
    vec4 s = texture(u_state, vUV);
    float alive = step(0.1, s.a);
    vec3 color = clamp(s.rgb * 0.5 + 0.5, 0.0, 1.0);
    fragColor = vec4(color * alive, 1.0);
}
"""

_NCA_INTERACTION_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
uniform vec2 u_gridSize;
uniform int u_toggleCount;
uniform float u_brushRadius;
uniform vec2 u_toggles[64];
in vec2 vUV;
out vec4 fragColor;
void main() {
    vec4 s = texture(u_state, vUV);
    vec2 cell = min(floor(vUV * u_gridSize), u_gridSize - 1.0);
    for (int i = 0; i < 64; i++) {
        if (i >= u_toggleCount) break;
        vec2 tc = u_toggles[i];
        vec2 toggleCell = min(
            floor(vec2(tc.x, 1.0 - tc.y) * u_gridSize), u_gridSize - 1.0);
        float dist = max(abs(cell.x - toggleCell.x), abs(cell.y - toggleCell.y));
        if (dist <= u_brushRadius) {
            if (s.a > 0.1) {
                s = vec4(0.0, 0.0, 0.0, 0.0);
            } else {
                s = vec4(0.0, 0.0, 0.0, 1.0);
            }
            break;
        }
    }
    fragColor = s;
}
"""


class NCARepresentation(
    NetworkInspectable, Saveable, GridAnalyzable, RepresentationBase
):
    """
    Neural Cellular Automata: NEAT-evolved per-cell update rule, Sobel perception.

    Genome = neat.DefaultGenome (single network: 14 inputs -> 4 state-delta outputs).
    Uses grid substrate with RGBA16F; update rule is compiled via NcaRuleAssembler
    and passed per-pattern as rule in serialize_output.
    """

    id = "nca"
    frontend_metadata = {
        "hasSignalControls": True,
        "genomeKeys": ["nodes", "connections", "key"],
    }

    phenotype = Phenotype(
        substrate=Substrate(
            type="grid",
            grid_size=DEFAULT_GRID_SIZE,
            state_format="RGBA16F",
            wrap="CLAMP",
        ),
        display_rule=_NCA_DISPLAY_SHADER,
        meta_template="Nodes: {nodes} | Connections: {connections} · NCA",
        behaviour=Behaviour(
            update_rule=None,
            update_interval_ms=33,
            interaction_rule=_NCA_INTERACTION_SHADER,
            interactions=("toggle",),
        ),
    )

    def __init__(
        self,
        grid_size: int = DEFAULT_GRID_SIZE,
        nca_steps: int = DEFAULT_NCA_STEPS,
        neat_config_nca_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        from .. import experiment

        self.grid_size = grid_size
        self.nca_steps = nca_steps
        path = neat_config_nca_path or getattr(
            experiment, "NEAT_NCA_CONFIG_PATH", "config/neat/neat_config_nca.txt"
        )
        self.receptor = NeatReceptor(
            name="nca_update",
            inputs=catalog.NCA_NEAT_INPUTS,
            outputs=catalog.NCA_STATE_DELTA_OUTPUTS,
            config_path=path,
            role="primary",
        )
        self.interaction = Receptor(
            name="nca_signals",
            inputs=catalog.NCA_GLOBAL_INPUTS,
            outputs=(),
        )
        self.sensory_system = SensorySystem(
            receptors=(self.interaction,),
            outputs=(),
        )
        # Population sets innovation_tracker on config for create_random_genome
        self._population = neat.Population(self.config)

    @property
    def config(self) -> neat.Config:
        """NEAT config for the update-rule network."""
        return self.receptor.config

    def _seed_grid(self) -> np.ndarray:
        """Fixed initial seed (center pixel alive)."""
        return _create_seed(self.grid_size)

    def create_random(self, key: int = 0) -> neat.DefaultGenome:
        from ..genome.operators import create_random_genome

        genome = create_random_genome(self.config, genome_id=key)
        genome.key = key  # type: ignore[assignment]
        return genome

    def mutate(self, genome: neat.DefaultGenome, key: int) -> neat.DefaultGenome:
        child = mutate_genome(genome, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def crossover(
        self,
        a: neat.DefaultGenome,
        b: neat.DefaultGenome,
        key: int,
    ) -> neat.DefaultGenome:
        child = crossover_genomes(a, b, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def express(
        self,
        genome: neat.DefaultGenome,
        inputs: dict[str, float],
        **kwargs: Any,
    ) -> RepresentationOutput:
        steps = kwargs.get("nca_steps", self.nca_steps)
        preview_size = kwargs.get("nca_preview_grid_size")
        if preview_size is not None:
            preview_size = max(8, min(int(preview_size), self.grid_size))
            if preview_size >= self.grid_size:
                preview_size = None
        grid_size = preview_size if preview_size is not None else self.grid_size
        sig = np.array(
            [
                inputs.get("raw_time", 0.0),
                inputs.get("mouse_x", 0.5),
                inputs.get("mouse_y", 0.5),
                inputs.get("mouse_speed", 0.0),
            ],
            dtype=np.float64,
        )
        seed = _create_seed(grid_size)
        state = _run_nca_cpu_neat(seed, genome, self.receptor, steps, sig)
        rgb = _state_to_rgb(state)
        if preview_size is not None and grid_size < self.grid_size:
            # Upscale to full size for consistent card display (nearest-neighbor)
            factor = self.grid_size // grid_size
            rgb = np.repeat(np.repeat(rgb, factor, axis=0), factor, axis=1)
            rgb = rgb[: self.grid_size, : self.grid_size, :].copy()
        return RepresentationOutput("grid", rgb)

    def develop(
        self, genome: neat.DefaultGenome, color_mode: str | None = None
    ) -> str | None:
        """Return compiled NCA step shader for this genome."""
        contribution = self.receptor.compile(genome)
        return assemble_nca_step_shader(contribution)

    def to_json(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        return genome_to_json(genome)

    def from_json(self, data: dict[str, Any]) -> neat.DefaultGenome:
        return genome_from_json(data, self.config)

    def serialize_output(
        self,
        output: RepresentationOutput,
        genome: neat.DefaultGenome | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if output.output_type == "grid" and hasattr(output.data, "shape"):
            arr = np.asarray(output.data)
            result["image"] = "data:image/png;base64," + rgb_to_png_base64(arr)
            grid_01 = (np.asarray(arr)[:, :, 0] > 0).astype(np.uint8)
            if arr.shape[:2] != (self.grid_size, self.grid_size):
                grid_01 = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
            result["grid"] = grid_01.tolist()
        else:
            result["image"] = ""
            result["grid"] = []

        if genome is not None:
            result["rule"] = self.develop(genome)
            seed = self._seed_grid()
            result["grid"] = (seed[:, :, 3] > 0.1).astype(np.uint8).tolist()
            result["nodes"] = len(genome.nodes)
            result["connections"] = sum(
                1 for c in genome.connections.values() if c.enabled
            )
        return result

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self,
        genome: neat.DefaultGenome,
        individual_id: int,
        **kwargs: Any,
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        out = self.express(genome, {})
        if out.output_type != "grid" or not hasattr(out.data, "shape"):
            return {}
        arr = np.asarray(out.data)
        names = self.get_save_filenames(individual_id)
        return {
            names["png"]: to_png_bytes(arr),
            names["genome_json"]: json.dumps(self.to_json(genome), indent=2).encode(
                "utf-8"
            ),
        }

    def get_neat_pop_size(self) -> int | None:
        return getattr(self.config, "pop_size", None)

    # --- NetworkInspectable (brain view) ---

    def get_network_types(self) -> tuple[str, ...]:
        return (self.receptor.name,)

    def get_network_data(self, genome: neat.DefaultGenome) -> dict[str, Any] | None:
        nodes, connections = self.receptor.extract_network_data(genome, x_offset=0)
        return {"nodes": nodes, "connections": connections}

    def adjust_weight(
        self,
        genome: neat.DefaultGenome,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        if network != self.receptor.name:
            return None
        try:
            source_id = parse_network_node_id(source)
            target_id = parse_network_node_id(target)
        except (ValueError, TypeError):
            return None
        conn_key = (source_id, target_id)
        if conn_key not in genome.connections:
            return None
        genome.connections[conn_key].weight = weight
        rule_str = self.develop(genome) or ""
        return {"rule": rule_str, "individual": self.to_json(genome)}

"""
Conway's Game of Life (2D) representation.

Individual = initial 2D grid (alive/dead). Evolution mutates/crosses the initial
configuration. Output = grid (H×W×3 RGB). Click-to-kill zeroes cells in the
running simulation (frontend applies kill mask before each GOL step).
"""

from __future__ import annotations

import json
import random
from typing import Any, Callable

import numpy as np

from ..signals import catalog
from ..signals.receptor import Receptor
from ..signals.sensory_system import SensorySystem
from ._image_util import rgb_to_png_base64
from .base import RepresentationBase
from .mixins import GridAnalyzable, Saveable
from .protocol import Behaviour, Phenotype, RepresentationOutput, Substrate

# Default grid size for genome and simulation (same size).
DEFAULT_GRID_SIZE = 64
DEFAULT_GOL_STEPS = 48  # for express() final frame (lower = faster load)


class ConwayGenome:
    """
    Genome for Conway's Game of Life: initial 2D grid (0/1) and key (individual id).
    """

    __slots__ = ("grid", "key")

    def __init__(self, grid: np.ndarray, key: int = 0) -> None:
        self.grid = np.asarray(grid, dtype=np.uint8)
        self.key = key


def _step_gol(grid: np.ndarray) -> np.ndarray:
    """One step of Conway's Game of Life (B3/S23). Toroidal boundary."""
    h, w = grid.shape
    next_grid = np.zeros((h, w), dtype=np.uint8)
    for r in range(h):
        for c in range(w):
            count = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = (r + dr) % h, (c + dc) % w
                    count += grid[nr, nc]
            if count == 3 or (grid[r, c] == 1 and count == 2):
                next_grid[r, c] = 1
    return next_grid


def _run_gol(initial: np.ndarray, steps: int) -> np.ndarray:
    """Run GOL for `steps` steps; return final grid (H, W) 0/1."""
    grid = np.asarray(initial, dtype=np.uint8).copy()
    for _ in range(steps):
        grid = _step_gol(grid)
    return grid


def _grid_to_rgb(grid: np.ndarray) -> np.ndarray:
    """Convert (H, W) 0/1 grid to (H, W, 3) RGB; 0=black, 1=white."""
    h, w = grid.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[grid == 1] = 255
    return rgb


def _grid_to_nested_list(grid: np.ndarray) -> list[list[int]]:
    """Convert ndarray to JSON-serializable nested list."""
    return grid.tolist()


def _nested_list_to_grid(data: list[list[int]] | list[list[float]]) -> np.ndarray:
    """Convert nested list to (H, W) uint8 grid."""
    arr = np.asarray(data, dtype=np.float64)
    return (arr > 0.5).astype(np.uint8)


# GLSL for grid substrate: GOL step, display (grayscale), toggle (click).
# Frontend runs step to FBO, display to screen; toggle applies brush before step.
_GOL_FRAGMENT_SHADER = """#version 300 es
precision highp float;

uniform sampler2D u_state;
uniform vec2 u_texelSize;

in vec2 vUV;
out vec4 fragColor;

void main() {
    float c = texture(u_state, vUV).r;
    float n = 0.0;
    n += texture(u_state, vUV + vec2(-u_texelSize.x, -u_texelSize.y)).r;
    n += texture(u_state, vUV + vec2(-u_texelSize.x, 0.0)).r;
    n += texture(u_state, vUV + vec2(-u_texelSize.x, u_texelSize.y)).r;
    n += texture(u_state, vUV + vec2(0.0, -u_texelSize.y)).r;
    n += texture(u_state, vUV + vec2(0.0, u_texelSize.y)).r;
    n += texture(u_state, vUV + vec2(u_texelSize.x, -u_texelSize.y)).r;
    n += texture(u_state, vUV + vec2(u_texelSize.x, 0.0)).r;
    n += texture(u_state, vUV + vec2(u_texelSize.x, u_texelSize.y)).r;
    float next = (n > 2.5 && n < 3.5) || (c > 0.5 && n > 1.5 && n < 3.5) ? 1.0 : 0.0;
    fragColor = vec4(next, next, next, 1.0);
}
"""

_CA_DISPLAY_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
in vec2 vUV;
out vec4 fragColor;
void main() {
  float v = texture(u_state, vUV).r;
  fragColor = vec4(v, v, v, 1.0);
}
"""

_CA_TOGGLE_SHADER = """#version 300 es
precision highp float;
uniform sampler2D u_state;
uniform vec2 u_gridSize;
uniform int u_toggleCount;
uniform float u_brushRadius;
uniform vec2 u_toggles[64];
in vec2 vUV;
out vec4 fragColor;
void main() {
  float v = texture(u_state, vUV).r;
  vec2 cell = min(floor(vUV * u_gridSize), u_gridSize - 1.0);
  for (int i = 0; i < 64; i++) {
    if (i >= u_toggleCount) break;
    vec2 tc = u_toggles[i];
    vec2 toggleCell = min(floor(vec2(tc.x, 1.0 - tc.y) * u_gridSize), u_gridSize - 1.0);
    float dist = max(abs(cell.x - toggleCell.x), abs(cell.y - toggleCell.y));
    if (dist <= u_brushRadius) {
      v = 1.0 - v;
      break;
    }
  }
  fragColor = vec4(v, v, v, 1.0);
}
"""


class ConwayRepresentation(Saveable, GridAnalyzable, RepresentationBase):
    """
    Representation for Conway's Game of Life (2D).
    Individual = ConwayGenome (initial grid); output = grid (H×W×3 RGB).

    Declares interaction signals (mouse_x, mouse_y) in its sensory_system.
    Internal routing maps these to the toggleMask / onCellInteraction
    mechanism on the frontend.
    """

    id = "ca"
    frontend_metadata = {
        "hasSignalControls": False,
        "genomeKeys": ["grid", "key"],
    }

    phenotype = Phenotype(
        substrate=Substrate(
            type="grid",
            grid_size=DEFAULT_GRID_SIZE,
            state_format="RGBA",
            wrap="REPEAT",
        ),
        display_rule=_CA_DISPLAY_SHADER,
        meta_template="{fingerprint} · {density} · {live_count} alive",
        behaviour=Behaviour(
            update_rule=_GOL_FRAGMENT_SHADER,
            update_interval_ms=180,
            interaction_rule=_CA_TOGGLE_SHADER,
            interactions=("toggle",),
        ),
    )

    def __init__(
        self,
        grid_size: int = DEFAULT_GRID_SIZE,
        gol_steps: int = DEFAULT_GOL_STEPS,
        **kwargs: Any,
    ) -> None:
        self.grid_size = grid_size
        self.gol_steps = gol_steps

        # -- Receptor: interaction signal translation (mouse_x, mouse_y for frontend) --
        self.interaction = Receptor(
            name="interaction",
            inputs=catalog.CA_INTERACTION_INPUTS,
            outputs=(),
        )

        # -- Public sensory system (receptor-centric) --
        self.sensory_system = SensorySystem(
            receptors=(self.interaction,),
            outputs=(),
        )

    def create_random(self, key: int = 0) -> ConwayGenome:
        n = self.grid_size
        density = 0.25 + random.random() * 0.15  # 25–40%
        grid = (np.random.random((n, n)) < density).astype(np.uint8)
        return ConwayGenome(grid=grid, key=key)

    def mutate(self, genome: ConwayGenome, key: int) -> ConwayGenome:
        grid = genome.grid.copy()
        n = grid.shape[0]
        r, c = random.randint(0, n - 1), random.randint(0, n - 1)
        grid[r, c] = 1 - grid[r, c]
        return ConwayGenome(grid=grid, key=key)

    def crossover(self, a: ConwayGenome, b: ConwayGenome, key: int) -> ConwayGenome:
        ga, gb = a.grid, b.grid
        h, w = ga.shape
        mask = np.random.randint(0, 2, (h, w), dtype=np.uint8)
        grid = np.where(mask, ga, gb)
        return ConwayGenome(grid=grid, key=key)

    def express(
        self, genome: ConwayGenome, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        steps = kwargs.get("gol_steps", self.gol_steps)
        grid = _run_gol(genome.grid, steps)
        rgb = _grid_to_rgb(grid)
        return RepresentationOutput("grid", rgb)

    def to_json(self, genome: ConwayGenome) -> dict[str, Any]:
        return {"key": genome.key, "grid": _grid_to_nested_list(genome.grid)}

    def from_json(self, data: dict[str, Any]) -> ConwayGenome:
        key = int(data.get("key", 0))
        grid_data = data.get("grid", [])
        if grid_data:
            grid = _nested_list_to_grid(grid_data)
        else:
            grid = np.zeros((DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE), dtype=np.uint8)
        return ConwayGenome(grid=grid, key=key)

    def serialize_output(
        self,
        output: RepresentationOutput,
        genome: ConwayGenome | None = None,
    ) -> dict[str, Any]:
        """Return image (base64) and grid for API. Rules come from phenotype.behaviour.
        When genome is provided, includes genome grid for client."""
        result: dict[str, Any]
        if output.output_type != "grid" or not hasattr(output.data, "shape"):
            result = {"image": "", "grid": []}
        else:
            arr = np.asarray(output.data)
            b64 = rgb_to_png_base64(arr)
            grid_01 = (arr[:, :, 0] > 127).astype(np.uint8)
            result = {
                "image": "data:image/png;base64," + b64,
                "grid": _grid_to_nested_list(grid_01),
            }
        if genome is not None:
            result["grid"] = _grid_to_nested_list(genome.grid)
        return result

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, genome: ConwayGenome, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] = kwargs.get("to_png_bytes")
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

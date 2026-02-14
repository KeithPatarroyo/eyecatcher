"""
Conway's Game of Life (2D) representation.

Individual = initial 2D grid (alive/dead). Evolution mutates/crosses the initial
configuration. Output = grid (H×W×3 RGB). Click-to-kill zeroes cells in the
running simulation (frontend applies kill mask before each GOL step).
"""

from __future__ import annotations

import base64
import io
import json
import random
from typing import Any, Callable

import numpy as np

from ..signals import catalog
from ..signals.spec import SignalSpec
from .base import RepresentationBase
from .protocol import OutputType, RepresentationOutput
from .sockets import GridSocket

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


def _rgb_to_png_base64(arr: np.ndarray) -> str:
    """Encode (H, W, 3) uint8 RGB array as PNG base64 (no data URL prefix)."""
    from PIL import Image

    arr = np.asarray(arr)
    if arr.ndim != 3 or arr.shape[2] != 3:
        arr = np.stack([arr, arr, arr], axis=-1) if arr.ndim == 2 else arr
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0, 255)).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _nested_list_to_grid(data: list[list[int]] | list[list[float]]) -> np.ndarray:
    """Convert nested list to (H, W) uint8 grid."""
    arr = np.asarray(data, dtype=np.float64)
    return (arr > 0.5).astype(np.uint8)


class ConwayRepresentation(RepresentationBase):
    """
    Representation for Conway's Game of Life (2D).
    Individual = ConwayGenome (initial grid); output = grid (H×W×3 RGB).

    Declares interaction signals (mouse_x, mouse_y) in its signal_spec.
    Internal routing maps these to the toggleMask / onCellInteraction
    mechanism on the frontend.
    """

    id = "ca"
    output_type: OutputType = "grid"
    frontend_metadata = {
        "hasSignalControls": False,
        "genomeKeys": ["grid", "key"],
        "adapterFactory": None,
    }

    def __init__(
        self,
        grid_size: int = DEFAULT_GRID_SIZE,
        gol_steps: int = DEFAULT_GOL_STEPS,
        **kwargs: Any,
    ) -> None:
        self.grid_size = grid_size
        self.gol_steps = gol_steps

        # -- Socket: interaction signal translation --
        self.interaction = GridSocket(
            "interaction",
            inputs=catalog.CA_INTERACTION_INPUTS,
            grid_size=grid_size,
        )

        # -- Public signal spec (socket-centric) --
        self.signal_spec = SignalSpec(
            sockets=(self.interaction,),
            outputs=(),
        )

    def create_random(self, key: int = 0) -> ConwayGenome:
        n = self.grid_size
        density = 0.25 + random.random() * 0.15  # 25–40%
        grid = (np.random.random((n, n)) < density).astype(np.uint8)
        return ConwayGenome(grid=grid, key=key)

    def mutate(self, ind: ConwayGenome, key: int) -> ConwayGenome:
        grid = ind.grid.copy()
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
        self, ind: ConwayGenome, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        steps = kwargs.get("gol_steps", self.gol_steps)
        grid = _run_gol(ind.grid, steps)
        rgb = _grid_to_rgb(grid)
        return RepresentationOutput("grid", rgb)

    def compile_to_shader(
        self, ind: ConwayGenome, color_mode: str | None = None
    ) -> str | None:
        """GLSL for Conway GOL (step + display). Frontend uses two passes with FBOs."""
        return _GOL_FRAGMENT_SHADER

    def to_json(self, ind: ConwayGenome) -> dict[str, Any]:
        return {"key": ind.key, "grid": _grid_to_nested_list(ind.grid)}

    def from_json(self, data: dict[str, Any]) -> ConwayGenome:
        key = int(data.get("key", 0))
        grid_data = data.get("grid", [])
        if grid_data:
            grid = _nested_list_to_grid(grid_data)
        else:
            grid = np.zeros((DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE), dtype=np.uint8)
        return ConwayGenome(grid=grid, key=key)

    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        if out.output_type != "grid" or not hasattr(out.data, "shape"):
            return None
        grid = np.asarray(out.data)
        if grid.ndim == 3:
            grid = grid[:, :, 0]
        return grid if grid.ndim >= 2 else None

    def serialize_individual_extra(self, ind: ConwayGenome) -> dict[str, Any]:
        return {"grid": _grid_to_nested_list(ind.grid)}

    def serialize_express_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """Return image (base64), shader (GOL), and grid (nested list) for API."""
        if output.output_type != "grid" or not hasattr(output.data, "shape"):
            return {"image": "", "shader": _GOL_FRAGMENT_SHADER, "grid": []}
        arr = np.asarray(output.data)
        b64 = _rgb_to_png_base64(arr)
        grid_01 = (arr[:, :, 0] > 127).astype(np.uint8)
        return {
            "image": "data:image/png;base64," + b64,
            "shader": _GOL_FRAGMENT_SHADER,
            "grid": _grid_to_nested_list(grid_01),
        }

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: ConwayGenome, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        out = self.express(ind, {})
        if out.output_type != "grid" or not hasattr(out.data, "shape"):
            return {}
        arr = np.asarray(out.data)
        names = self.get_save_filenames(individual_id)
        return {
            names["png"]: to_png_bytes(arr),
            names["genome_json"]: json.dumps(self.to_json(ind), indent=2).encode(
                "utf-8"
            ),
        }


# Fragment shader: Conway GOL step. Reads u_state, outputs next (R = alive).
# Frontend runs this to a FBO, then displays by sampling that texture.
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

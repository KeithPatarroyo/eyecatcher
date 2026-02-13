"""
Elementary Cellular Automata (1D) substrate for testing the substrate protocol.

Individual = CARule (8-bit Wolfram rule). Output = grid (generations × width × 3 RGB).
"""

from __future__ import annotations

import json
import random
from typing import Any, Callable

import numpy as np

from .protocol import OutputType, SubstrateOutput


class CARule:
    """
    Elementary CA rule: 8-bit integer 0–255 (Wolfram rule number).
    key is used as individual id for evolution/API.
    """

    __slots__ = ("rule", "key")

    def __init__(self, rule: int, key: int = 0) -> None:
        self.rule = rule & 0xFF
        self.key = key


def _step_1d_ca(row: np.ndarray, rule: int) -> np.ndarray:
    """Next row from current using elementary rule (periodic boundary)."""
    n = len(row)
    next_row = np.zeros(n, dtype=np.uint8)
    for i in range(n):
        left = row[(i - 1) % n]
        center = row[i]
        right = row[(i + 1) % n]
        idx = (left << 2) | (center << 1) | right
        next_row[i] = (rule >> idx) & 1
    return next_row


def _run_ca(
    rule: int,
    width: int,
    generations: int,
    seed_center: bool = True,
) -> np.ndarray:
    """
    Run 1D CA for `generations` steps; return grid (generations, width) with 0/1.
    If seed_center, first row has a single 1 in the middle; else random.
    """
    row = np.zeros(width, dtype=np.uint8)
    if seed_center:
        row[width // 2] = 1
    else:
        row[:] = np.random.randint(0, 2, size=width)
    grid = np.zeros((generations, width), dtype=np.uint8)
    grid[0] = row
    for t in range(1, generations):
        row = _step_1d_ca(row, rule)
        grid[t] = row
    return grid


def _grid_to_rgb(grid: np.ndarray) -> np.ndarray:
    """Convert (H, W) 0/1 grid to (H, W, 3) RGB; 0=black, 1=white."""
    h, w = grid.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[grid == 1] = 255
    return rgb


class ElementaryCASubstrate:
    """
    Substrate for elementary 1D cellular automata (Wolfram rules).
    Individual = CARule; output = grid (H×W×3 RGB).
    """

    id = "ca"
    output_type: OutputType = "grid"

    def __init__(
        self,
        width: int = 256,
        generations: int = 128,
        seed_center: bool = True,
        **kwargs: Any,
    ) -> None:
        self.width = width
        self.generations = generations
        self.seed_center = seed_center

    def create_random(self, key: int = 0) -> CARule:
        return CARule(rule=random.randint(0, 255), key=key)

    def mutate(self, ind: CARule, key: int) -> CARule:
        bit = random.randint(0, 7)
        new_rule = ind.rule ^ (1 << bit)
        return CARule(rule=new_rule, key=key)

    def crossover(self, a: CARule, b: CARule, key: int) -> CARule:
        mask = random.randint(0, 255)
        new_rule = (a.rule & mask) | (b.rule & (~mask & 0xFF))
        return CARule(rule=new_rule, key=key)

    def evaluate(
        self, ind: CARule, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        width = kwargs.get("width", self.width)
        generations = kwargs.get("generations", self.generations)
        seed_center = kwargs.get("seed_center", self.seed_center)
        grid = _run_ca(ind.rule, width, generations, seed_center=seed_center)
        rgb = _grid_to_rgb(grid)
        return SubstrateOutput("grid", rgb)

    def compile_to_shader(
        self, ind: CARule, color_mode: str | None = None
    ) -> str | None:
        """GLSL shader for 1D CA; uRule, uGeneration. One row per 0.5s."""
        return _CA_FRAGMENT_SHADER

    def to_json(self, ind: CARule) -> dict[str, Any]:
        return {"rule": ind.rule, "key": ind.key}

    def from_json(self, data: dict[str, Any]) -> CARule:
        rule = int(data.get("rule", 0)) & 0xFF
        key = int(data.get("key", 0))
        return CARule(rule=rule, key=key)

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: CARule, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        out = self.evaluate(ind, {})
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


# Grid size for CA display; 36 = chunky, readable cells.
CA_GRID_SIZE = 36

# GLSL fragment shader for 1D CA. Row 0 = seed; rows grow over time.
# Uniforms: uRule, uGeneration (0–1), uResolution, uGridSize.
_CA_FRAGMENT_SHADER = """#version 300 es
precision highp float;

uniform int uRule;
uniform float uGeneration;
uniform vec2 uResolution;
uniform int uGridSize;

in vec2 vUV;
out vec4 fragColor;

int wrap(int c, int w) {
    int cw = c % w;
    if (cw < 0) cw += w;
    return cw;
}

float seed_val(int c, int w, int center) {
    return (wrap(c, w) == center) ? 1.0 : 0.0;
}

float rule_bit(float a, float b, float c) {
    int ia = int(step(0.5, a));
    int ib = int(step(0.5, b));
    int ic = int(step(0.5, c));
    int idx = ia * 4 + ib * 2 + ic;
    int bit = (uRule >> idx) & 1;
    return float(bit);
}

void main() {
    int g = max(uGridSize, 1);
    int col = int(gl_FragCoord.x * float(g) / uResolution.x);
    int row = g - 1 - int(gl_FragCoord.y * float(g) / uResolution.y);
    int maxRows = int(uGeneration * float(g));
    if (row < 0 || row >= maxRows) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    int w = g;
    int h = g;
    int center = w / 2;
    float v0 = seed_val(col - 2, w, center);
    float v1 = seed_val(col - 1, w, center);
    float v2 = seed_val(col, w, center);
    float v3 = seed_val(col + 1, w, center);
    float v4 = seed_val(col + 2, w, center);
    for (int r = 1; r <= 256; r++) {
        if (r > row) break;
        float n0 = rule_bit(v0, v1, v2);
        float n1 = rule_bit(v1, v2, v3);
        float n2 = rule_bit(v2, v3, v4);
        float n3 = rule_bit(v3, v4, v0);
        float n4 = rule_bit(v4, v0, v1);
        v0 = n0; v1 = n1; v2 = n2; v3 = n3; v4 = n4;
    }
    float v = v2;
    fragColor = vec4(v, v, v, 1.0);
}
"""

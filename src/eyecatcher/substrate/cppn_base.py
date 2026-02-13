"""
Shared CPPN substrate helpers: NEAT config loading, query, render, and evaluate.

CPPNSubstrateBase implements shared logic for SingleCPPNSubstrate and DualCPPNSubstrate.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable as Cb
from collections.abc import Sequence
from typing import Any

import neat
import numpy as np

from .. import get_root_dir
from ..evolution import DEFAULT_RENDER_RESOLUTION
from ..genome.activation import register_custom_activations
from ..signals.registry import (
    apply_derived_inputs,
    get_default_signal_values,
    inputs_array,
)
from ..signals.validation import validate_neat_config
from .protocol import SubstrateOutput


def normalize_to_bipolar(val: float) -> float:
    """Map value from [0, 1] to [-1, 1]."""
    return val * 2.0 - 1.0


def _clamp_rgb(out: list[float]) -> tuple[float, float, float]:
    """Convert three bipolar outputs to 0–1 RGB."""
    r = max(0.0, min(1.0, (out[0] + 1.0) / 2.0))
    g = max(0.0, min(1.0, (out[1] + 1.0) / 2.0))
    b = max(0.0, min(1.0, (out[2] + 1.0) / 2.0))
    return r, g, b


def _load_neat_config(
    path: str | None,
    default_path: str,
    signals_in: Sequence[Any],
    signals_out: Sequence[Any],
    label: str,
) -> neat.Config:
    """Load NEAT config; resolve path; register activations; validate."""
    import os

    root = get_root_dir()
    resolved = path or default_path
    if not os.path.isabs(resolved):
        resolved = os.path.join(root, resolved)
    config = neat.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        resolved,
    )
    register_custom_activations(config)
    validate_neat_config(config, list(signals_in), list(signals_out), label)
    return config


def query_neat_network(
    genome: neat.DefaultGenome,
    config: neat.Config,
    signals: Sequence[Any],
    derived: list,
    values: dict[str, float],
) -> list[float]:
    """Run network: fill defaults, apply derived inputs, return raw outputs."""
    full = {s.id: values.get(s.id, s.default) for s in signals}
    apply_derived_inputs(full, derived)
    in_arr = inputs_array(signals, full)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    return net.activate(in_arr)


def _rgb_uint8(r: float, g: float, b: float) -> list[int]:
    """Convert 0–1 RGB floats to uint8 list for image pixel."""
    return [int(r * 255), int(g * 255), int(b * 255)]


def render_pixel_grid(
    resolution: int,
    base_inputs: dict,
    query_fn: Cb[[dict], tuple[float, float, float]],
) -> np.ndarray:
    """Fill (res, res, 3) image via query_fn per pixel (base_inputs + x, y)."""
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = normalize_to_bipolar(i / resolution)
            y = normalize_to_bipolar(j / resolution)
            inputs = {**base_inputs, "x": x, "y": y}
            r, g, b = query_fn(inputs)
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def base_evaluate(compile_fn: Cb[[Any], str | None], ind: Any) -> SubstrateOutput:
    """Wrap compile_to_shader result in SubstrateOutput."""
    glsl = compile_fn(ind)
    return SubstrateOutput("shader", glsl if glsl else "")


def compile_with_color_mode(
    compiler: Any,
    ind: Any,
    color_mode: str | None,
    compile_fn: Cb[[Any, Any], str | None],
    *compile_args: Any,
) -> str | None:
    """Use one-off compiler if color_mode differs; else use given compiler."""
    if color_mode and color_mode != compiler.color_mode:
        alt = compiler.with_color_mode(color_mode)
        return compile_fn(alt, *compile_args)
    return compile_fn(compiler, *compile_args)


def _compute_network_stats(
    pairs: list[tuple[str, Any, neat.Config]],
) -> dict[str, Any]:
    """Return {label_nodes, label_connections, ...} for each (label, genome, config)."""
    result: dict[str, Any] = {}
    for label, genome, _config in pairs:
        nodes = getattr(genome, "nodes", {}) or {}
        conns = getattr(genome, "connections", {}) or {}
        result[f"{label}_nodes"] = len(nodes)
        result[f"{label}_connections"] = sum(
            1 for c in conns.values() if getattr(c, "enabled", True)
        )
    return result


class CPPNSubstrateBase(ABC):
    """
    Shared base for single and dual CPPN substrates.
    Subclasses implement query_rgb, _sample_inputs, get_base_inputs_for_render,
    compile_to_shader, to_json, from_json, create_random, mutate, crossover.
    """

    @abstractmethod
    def query_rgb(
        self, ind: Any, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        """Return (r, g, b) in 0–1 for this individual and inputs."""
        ...

    @abstractmethod
    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        """Build input dict for one sample point."""
        ...

    @abstractmethod
    def get_base_inputs_for_render(self) -> dict[str, float]:
        """Base inputs for render_to_image (e.g. default_inputs for the network)."""
        ...

    @abstractmethod
    def _compile(self, compiler: Any, ind: Any) -> str | None:
        """Compile individual to GLSL using the given compiler. Subclass-specific."""
        ...

    def compile_to_shader(self, ind: Any, color_mode: str | None = None) -> str | None:
        """Compile individual to GLSL fragment shader string."""
        return compile_with_color_mode(
            self.compiler, ind, color_mode, self._compile, ind
        )

    @abstractmethod
    def to_json(self, ind: Any) -> dict[str, Any]:
        """Serialize individual to JSON-serializable dict."""
        ...

    @abstractmethod
    def from_json(self, data: dict[str, Any]) -> Any:
        """Deserialize individual from dict."""
        ...

    def evaluate(
        self, ind: Any, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        """Wrap compile_to_shader in SubstrateOutput."""
        return base_evaluate(lambda i: self.compile_to_shader(i), ind)

    def sample_rgb(
        self,
        ind: Any,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        """Sample RGB at each (x, y) with shared time/signal base."""
        base = get_default_signal_values(time)
        return [
            list(self.query_rgb(ind, self._sample_inputs(x, y, time, base)))
            for x, y in coords
        ]

    def render_to_image(
        self,
        ind: Any,
        resolution: int | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        """Render individual to (resolution, resolution, 3) RGB image."""
        if resolution is None:
            resolution = DEFAULT_RENDER_RESOLUTION
        return render_pixel_grid(
            resolution,
            self.get_base_inputs_for_render(),
            lambda inputs: self.query_rgb(ind, inputs),
        )

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """Common filenames for save bundle; subclasses may override to add keys."""
        return {
            "png": f"pattern_{individual_id}.png",
            "glsl": f"pattern_{individual_id}.glsl",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: Any, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """Common save assets (png, glsl, genome_json). Override to add more."""
        to_png_bytes: Cb[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        names = self.get_save_filenames(individual_id)
        shader_code = self.compile_to_shader(ind) or ""
        img = self.render_to_image(ind, resolution=DEFAULT_RENDER_RESOLUTION)
        json_bytes = json.dumps(self.to_json(ind), indent=2).encode("utf-8")
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["genome_json"]: json_bytes,
        }

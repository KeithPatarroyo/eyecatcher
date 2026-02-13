"""
Shared CPPN substrate helpers: NEAT config loading, query, render, and evaluate.

Used by DualCPPNSubstrate and SingleCPPNSubstrate. Query and rendering logic
moved here from evaluation.query and evaluation.rendering.
"""

from __future__ import annotations

from collections.abc import Callable as Cb
from collections.abc import Sequence
from typing import Any

import neat
import numpy as np

from .. import get_root_dir
from ..lib.math_utils import normalize_to_bipolar
from ..signals.activation import register_custom_activations
from ..signals.signals import apply_derived_inputs, inputs_array
from ..signals.validation import validate_neat_config
from .protocol import SubstrateOutput


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


def render_frames(
    render_fn: Cb[[float], np.ndarray],
    time_range: tuple[float, float],
    num_frames: int,
    include_end_frame: bool,
) -> list:
    """Return list of frames by calling render_fn(t) for t in time_range."""
    start_time, end_time = time_range
    frames = []
    for frame_idx in range(num_frames):
        denom = max(1, num_frames - 1) if include_end_frame else num_frames
        t = start_time + (end_time - start_time) * (frame_idx / denom)
        frames.append(render_fn(t))
    return frames


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
        from ..glsl import ShaderCompiler

        alt = ShaderCompiler(color_mode=color_mode)
        return compile_fn(alt, *compile_args)
    return compile_fn(compiler, *compile_args)

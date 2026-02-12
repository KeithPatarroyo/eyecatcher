"""
Rendering: full-image and animation frame generation from CPPNs.

Shared helpers _render_pixel_grid, _render_frames. Single-CPPN: render_image,
render_animation_frames. Dual-CPPN rendering lives on DualCPPNSubstrate.render_to_image.
"""

from typing import Callable, Optional

import neat
import numpy as np

from ..algorithm import config as evolution_config
from ..lib.math_utils import normalize_to_bipolar
from ..signals.signals import (
    VISUAL_INPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
)
from .query import query_visual_cppn


def _rgb_uint8(r: float, g: float, b: float) -> list[int]:
    """Convert 0–1 RGB floats to uint8 list for image pixel."""
    return [int(r * 255), int(g * 255), int(b * 255)]


def _render_pixel_grid(
    resolution: int,
    base_inputs: dict,
    query_fn: Callable[[dict], tuple[float, float, float]],
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


def _render_frames(
    render_fn: Callable[[float], np.ndarray],
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


def render_image(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    resolution: Optional[int] = None,
    time: float = 0.0,
    extra_inputs: Optional[dict] = None,
) -> np.ndarray:
    """Render a full image from a single visual CPPN at a given time."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    base = default_inputs(VISUAL_INPUTS)
    base[VISUAL_TIME_INPUT_NAME] = normalize_to_bipolar(time)
    if extra_inputs:
        base.update(extra_inputs)

    def query(inputs):
        return query_visual_cppn(genome, visual_config, inputs)

    return _render_pixel_grid(resolution, base, query)


def render_animation_frames(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    resolution: Optional[int] = None,
    num_frames: Optional[int] = None,
    time_range: tuple[float, float] = (0.0, 1.0),
) -> list:
    """Render multiple frames (single-CPPN)."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    if num_frames is None:
        num_frames = evolution_config.DEFAULT_NUM_FRAMES
    return _render_frames(
        lambda t: render_image(genome, visual_config, resolution, t),
        time_range,
        num_frames,
        include_end_frame=False,
    )

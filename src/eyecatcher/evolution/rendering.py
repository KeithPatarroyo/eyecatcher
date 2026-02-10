"""
Rendering: full-image and animation frame generation from CPPNs.
"""

from typing import Optional

import neat
import numpy as np

from . import config as evolution_config
from .genome import DualGenome
from .query import query_dual_cppn, query_visual_cppn
from .signals import (
    TIME_CPPN_TIME_INPUT_NAME,
    TIME_INPUTS,
    VISUAL_INPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
)


def _rgb_uint8(r: float, g: float, b: float) -> list[int]:
    """Convert 0–1 RGB floats to uint8 list for image pixel."""
    return [int(r * 255), int(g * 255), int(b * 255)]


def render_image(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    resolution: Optional[int] = None,
    time: float = 0.0,
    extra_inputs: Optional[dict] = None,
) -> np.ndarray:
    """
    Render a full image from a single visual CPPN at a given time (single-CPPN path).

    Used by tests and any legacy single-genome flow.
    For dual-CPPN use render_dual_image.
    extra_inputs: optional dict of additional signal values (keys = signal names).
    Returns (H, W, 3) uint8 array.
    """
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    base = default_inputs(VISUAL_INPUTS)
    base[VISUAL_TIME_INPUT_NAME] = -1.0 + time * 2.0
    if extra_inputs:
        base.update(extra_inputs)
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = -1.0 + (i / resolution) * 2.0
            y = -1.0 + (j / resolution) * 2.0
            inputs = {**base, "x": x, "y": y}
            r, g, b = query_visual_cppn(genome, visual_config, inputs)
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def render_animation_frames(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    resolution: Optional[int] = None,
    num_frames: Optional[int] = None,
    time_range: tuple[float, float] = (0.0, 1.0),
) -> list:
    """Render multiple frames (single-CPPN; dual: render_dual_animation_frames)."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    if num_frames is None:
        num_frames = evolution_config.DEFAULT_NUM_FRAMES
    frames = []
    start_time, end_time = time_range
    for frame_idx in range(num_frames):
        t = start_time + (end_time - start_time) * (frame_idx / num_frames)
        frame = render_image(genome, visual_config, resolution, t)
        frames.append(frame)
    return frames


def render_dual_image(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    resolution: Optional[int] = None,
    extra_inputs: Optional[dict] = None,
) -> np.ndarray:
    """Render a complete image from a dual CPPN.

    extra_inputs: dict of signal name -> value (e.g. raw_time, mouse_speed).
    Keys and defaults come from the registry (evolution.signals).
    """
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    base = default_inputs(TIME_INPUTS)
    if extra_inputs:
        base.update(extra_inputs)
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = -1.0 + (i / resolution) * 2.0
            y = -1.0 + (j / resolution) * 2.0
            inputs = {**base, "x": x, "y": y}
            r, g, b = query_dual_cppn(dual_genome, visual_config, time_config, inputs)
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def render_dual_animation_frames(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    resolution: Optional[int] = None,
    num_frames: Optional[int] = None,
    time_range: tuple[float, float] = (0.0, 1.0),
    extra_inputs: Optional[dict] = None,
) -> list:
    """Render multiple frames for a dual CPPN animation.

    The time CPPN's first input (raw time) is varied over time_range.
    extra_inputs: optional base dict of other signal values (from registry).
    """
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    if num_frames is None:
        num_frames = evolution_config.DEFAULT_NUM_FRAMES
    time_key = TIME_CPPN_TIME_INPUT_NAME
    frames = []
    start_time, end_time = time_range
    for frame_idx in range(num_frames):
        t = start_time + (end_time - start_time) * (frame_idx / max(1, num_frames - 1))
        frame_inputs = dict(extra_inputs) if extra_inputs else {}
        frame_inputs[time_key] = -1.0 + t * 2.0
        frame = render_dual_image(
            dual_genome,
            visual_config,
            time_config,
            resolution,
            extra_inputs=frame_inputs,
        )
        frames.append(frame)
    return frames

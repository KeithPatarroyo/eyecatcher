"""
Rendering: full-image and animation frame generation from CPPNs.
"""

from typing import Optional

import neat
import numpy as np

from . import config as evolution_config
from .genome import DualGenome
from .query import query_cppn, query_dual_cppn


def _rgb_uint8(r: float, g: float, b: float) -> list[int]:
    """Convert 0–1 RGB floats to uint8 list for image pixel."""
    return [int(r * 255), int(g * 255), int(b * 255)]


def render_image(
    genome: neat.DefaultGenome,
    config: neat.Config,
    resolution: Optional[int] = None,
    time: float = 0.0,
) -> np.ndarray:
    """
    Render a full image from a CPPN at a given time.

    Returns (H, W, 3) uint8 array.
    """
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = -1.0 + (i / resolution) * 2.0
            y = -1.0 + (j / resolution) * 2.0
            t = -1.0 + time * 2.0
            r, g, b = query_cppn(genome, config, x, y, t)
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def render_animation_frames(
    genome: neat.DefaultGenome,
    config: neat.Config,
    resolution: Optional[int] = None,
    num_frames: Optional[int] = None,
    time_range: tuple[float, float] = (0.0, 1.0),
) -> list:
    """Render multiple frames for animation."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    if num_frames is None:
        num_frames = evolution_config.DEFAULT_NUM_FRAMES
    frames = []
    start_time, end_time = time_range
    for frame_idx in range(num_frames):
        t = start_time + (end_time - start_time) * (frame_idx / num_frames)
        frame = render_image(genome, config, resolution, t)
        frames.append(frame)
    return frames


def render_dual_image(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    resolution: Optional[int] = None,
    raw_time: float = 0.5,
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
) -> np.ndarray:
    """Render a complete image from a dual CPPN at a given raw time."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = -1.0 + (i / resolution) * 2.0
            y = -1.0 + (j / resolution) * 2.0
            r, g, b = query_dual_cppn(
                dual_genome,
                visual_config,
                time_config,
                x,
                y,
                raw_time,
                mouse_speed,
                mouse_distance,
                inactivity,
            )
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def render_dual_animation_frames(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    resolution: Optional[int] = None,
    num_frames: Optional[int] = None,
    time_range: tuple[float, float] = (0.0, 1.0),
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
) -> list:
    """Render multiple frames for a dual CPPN animation."""
    if resolution is None:
        resolution = evolution_config.PREVIEW_RENDER_RESOLUTION
    if num_frames is None:
        num_frames = evolution_config.DEFAULT_NUM_FRAMES
    frames = []
    start_time, end_time = time_range
    for frame_idx in range(num_frames):
        raw_t = start_time + (end_time - start_time) * (
            frame_idx / max(1, num_frames - 1)
        )
        frame = render_dual_image(
            dual_genome,
            visual_config,
            time_config,
            resolution,
            raw_time=raw_t,
            mouse_speed=mouse_speed,
            mouse_distance=mouse_distance,
            inactivity=inactivity,
        )
        frames.append(frame)
    return frames

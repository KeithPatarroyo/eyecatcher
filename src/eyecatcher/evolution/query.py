"""
CPPN evaluation: query networks for RGB and time signal outputs.
"""

from typing import Optional

import neat
import numpy as np

from .genome import DualGenome


def query_time_signal(
    time_genome: neat.DefaultGenome,
    time_config: neat.Config,
    raw_time: float,
    mouse_speed: float,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
) -> float:
    """Query time signal CPPN for modified time. Returns value in -1 to 1."""
    inputs = [raw_time, mouse_speed, mouse_distance, inactivity, 1.0]
    net = neat.nn.FeedForwardNetwork.create(time_genome, time_config)
    outputs = net.activate(inputs)
    return max(-1.0, min(1.0, outputs[0]))


def query_cppn(
    genome: neat.DefaultGenome,
    config: neat.Config,
    x: float,
    y: float,
    time: float = 0.0,
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
    distance: Optional[float] = None,
) -> tuple[float, float, float]:
    """Query visual CPPN for RGB at (x, y, time). Returns (r, g, b) in 0–1."""
    if distance is None:
        distance = float(np.sqrt(x**2 + y**2))
    inputs = [x, y, distance, time, mouse_speed, mouse_distance, inactivity, 1.0]
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    outputs = net.activate(inputs)
    r = max(0.0, min(1.0, (outputs[0] + 1.0) / 2.0))
    g = max(0.0, min(1.0, (outputs[1] + 1.0) / 2.0))
    b = max(0.0, min(1.0, (outputs[2] + 1.0) / 2.0))
    return r, g, b


def query_dual_cppn(
    dual_genome: DualGenome,
    config: neat.Config,
    time_config: neat.Config,
    x: float,
    y: float,
    raw_time: float = 0.0,
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
    distance: Optional[float] = None,
) -> tuple[float, float, float]:
    """Query dual CPPN for RGB at (x,y,raw_time). Returns (r,g,b) in 0–1."""
    modified_time = query_time_signal(
        dual_genome.time_signal,
        time_config,
        raw_time,
        mouse_speed,
        mouse_distance,
        inactivity,
    )
    return query_cppn(
        dual_genome.visual,
        config,
        x,
        y,
        modified_time,
        mouse_speed,
        mouse_distance,
        inactivity,
        distance,
    )

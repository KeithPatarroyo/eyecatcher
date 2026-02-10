"""
CPPN evaluation: query networks for RGB and time signal outputs.

Inputs are passed as a dict keyed by signal name (see evolution.signals).
Missing keys use the registry default, so adding a new input only requires
extending the registry; callers pass optional keys when available.
"""

import neat

from .genome import DualGenome
from .signals import (
    TIME_INPUTS,
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_TIME_INPUT_NAME,
    apply_derived_inputs,
    inputs_array,
)


def query_time_signal(
    time_genome: neat.DefaultGenome,
    time_config: neat.Config,
    inputs: dict[str, float],
) -> float:
    """Query time signal CPPN for modified time. Returns value in -1 to 1.

    inputs: dict of signal name -> value (e.g. raw_time, mouse_speed, ...).
    Missing keys use Signal.default from the registry.
    """
    in_arr = inputs_array(TIME_INPUTS, inputs)
    net = neat.nn.FeedForwardNetwork.create(time_genome, time_config)
    outputs = net.activate(in_arr)
    return max(-1.0, min(1.0, outputs[0]))


def query_visual_cppn(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    inputs: dict[str, float],
) -> tuple[float, float, float]:
    """Query visual CPPN for RGB. Returns (r, g, b) in 0–1.

    inputs: dict of signal name -> value (x, y, time, ...).
    Derived inputs (see signals.VISUAL_DERIVED_INPUTS) are computed when missing.
    Missing keys use Signal.default from the registry.
    """
    full = {s.name: inputs.get(s.name, s.default) for s in VISUAL_INPUTS}
    apply_derived_inputs(full, VISUAL_DERIVED_INPUTS)
    in_arr = inputs_array(VISUAL_INPUTS, full)
    net = neat.nn.FeedForwardNetwork.create(genome, visual_config)
    outputs = net.activate(in_arr)
    r = max(0.0, min(1.0, (outputs[0] + 1.0) / 2.0))
    g = max(0.0, min(1.0, (outputs[1] + 1.0) / 2.0))
    b = max(0.0, min(1.0, (outputs[2] + 1.0) / 2.0))
    return r, g, b


def query_dual_cppn(
    dual_genome: DualGenome,
    visual_config: neat.Config,
    time_config: neat.Config,
    inputs: dict[str, float],
) -> tuple[float, float, float]:
    """Query dual CPPN for RGB. Returns (r, g, b) in 0–1.

    inputs: dict with at least x, y and time-CPPN inputs (raw_time, ...).
    Modified time from the time CPPN is injected as 'time' for the visual CPPN.
    """
    modified_time = query_time_signal(
        dual_genome.time_signal,
        time_config,
        inputs,
    )
    time_key = VISUAL_TIME_INPUT_NAME
    visual_inputs = {**inputs, time_key: modified_time}
    return query_visual_cppn(dual_genome.visual, visual_config, visual_inputs)

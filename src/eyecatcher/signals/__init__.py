"""
Signal definitions and utilities for CPPN inputs/outputs.

Activation functions and custom registrations for NEAT.
"""

from .signals import (
    NETWORK_SIGNALS,
    TIME_CPPN_TIME_INPUT_NAME,
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    VISUAL_TIME_INPUT_NAME,
    apply_derived_inputs,
    build_glsl_input_map,
    default_inputs,
    input_labels,
    input_names,
    output_labels,
    output_names,
)

__all__ = [
    "VISUAL_INPUTS",
    "TIME_INPUTS",
    "VISUAL_OUTPUTS",
    "TIME_OUTPUTS",
    "NETWORK_SIGNALS",
    "VISUAL_TIME_INPUT_NAME",
    "TIME_CPPN_TIME_INPUT_NAME",
    "VISUAL_DERIVED_INPUTS",
    "apply_derived_inputs",
    "input_labels",
    "output_labels",
    "output_names",
    "input_names",
    "build_glsl_input_map",
    "default_inputs",
]

"""
Custom activation functions for NEAT CPPNs.

Register new activations here so they are available in NEAT configs.
register_custom_activations is called from substrate init (dual_cppn, single_cppn).
"""

import math

import neat


def _cos_activation(x: float) -> float:
    """Cosine activation function."""
    return math.cos(x)


def register_custom_activations(config: neat.Config) -> None:
    """Register custom activation functions with a NEAT config."""
    activation_defs = config.genome_config.activation_defs
    if "cos" not in activation_defs.functions:
        activation_defs.add("cos", _cos_activation)

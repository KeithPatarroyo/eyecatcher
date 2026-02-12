"""
NEAT config validation against signal registries.
"""

import neat


def validate_neat_config(
    config: neat.Config, signals, outputs, config_name: str
) -> None:
    """Assert NEAT config num_inputs/num_outputs match the signal registry."""
    actual_in = config.genome_config.num_inputs
    expected_in = len(signals)
    assert (
        actual_in == expected_in
    ), f"{config_name}: num_inputs={actual_in}, registry has {expected_in}"
    actual_out = config.genome_config.num_outputs
    expected_out = len(outputs)
    assert (
        actual_out == expected_out
    ), f"{config_name}: num_outputs={actual_out}, registry has {expected_out}"

"""
Single-CPPN substrate: visual network only (no time signal CPPN).

Individual = neat.DefaultGenome. Output = shader.
"""

from __future__ import annotations

import os
from typing import Any

import neat

from .. import get_root_dir
from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_single_genomes, mutate_single_genome
from ..genome.genome import create_random_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..glsl import ShaderCompiler
from ..signals.activation import register_custom_activations
from ..signals.signals import VISUAL_INPUTS, VISUAL_OUTPUTS
from .protocol import OutputType, SubstrateOutput


def _validate_visual_config(config: neat.Config) -> None:
    """Assert NEAT config num_inputs/num_outputs match visual registry."""
    gc = config.genome_config
    assert gc.num_inputs == len(
        VISUAL_INPUTS
    ), f"visual num_inputs={gc.num_inputs}, registry has {len(VISUAL_INPUTS)}"
    assert gc.num_outputs == len(
        VISUAL_OUTPUTS
    ), f"visual num_outputs={gc.num_outputs}, registry has {len(VISUAL_OUTPUTS)}"


class SingleCPPNSubstrate:
    """
    Substrate with a single visual CPPN (no time signal network).
    Individual = neat.DefaultGenome; output = shader.
    """

    id = "single_cppn"
    output_type: OutputType = "shader"

    def __init__(
        self,
        neat_config_path: str | None = None,
        color_mode: str = "hsv",
        **kwargs: Any,
    ) -> None:
        neat_config_path = neat_config_path or evolution_config.NEAT_CONFIG_PATH
        root = get_root_dir()
        if not os.path.isabs(neat_config_path):
            neat_config_path = os.path.join(root, neat_config_path)
        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            neat_config_path,
        )
        register_custom_activations(self.config)
        _validate_visual_config(self.config)
        # Prime config with innovation tracker (required by NEAT for
        # create_random/mutate/crossover)
        self._population = neat.Population(self.config)
        self.compiler = ShaderCompiler(color_mode=color_mode)

    def create_random(self, key: int = 0) -> neat.DefaultGenome:
        return create_random_genome(self.config, genome_id=key)

    def mutate(self, ind: neat.DefaultGenome, key: int) -> neat.DefaultGenome:
        child = mutate_single_genome(ind, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def crossover(
        self, a: neat.DefaultGenome, b: neat.DefaultGenome, key: int
    ) -> neat.DefaultGenome:
        child = crossover_single_genomes(a, b, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def evaluate(
        self, ind: neat.DefaultGenome, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        glsl = self.compile_to_shader(ind)
        if glsl:
            return SubstrateOutput("shader", glsl)
        return SubstrateOutput("shader", "")

    def compile_to_shader(self, ind: neat.DefaultGenome) -> str | None:
        return self.compiler.compile_to_glsl(ind, self.config)

    def to_json(self, ind: neat.DefaultGenome) -> dict[str, Any]:
        return genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> neat.DefaultGenome:
        return genome_from_json(data, self.config)

    def get_capabilities(self) -> dict[str, bool]:
        return {
            "save": True,
            "network": False,
            "time_output": False,
            "adjust_weight": False,
        }

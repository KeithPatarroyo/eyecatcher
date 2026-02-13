"""
Single-CPPN substrate: visual network only (no time signal CPPN).

Individual = neat.DefaultGenome. Output = shader.
"""

from __future__ import annotations

from typing import Any

import neat

from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_genomes, mutate_genome
from ..genome.genome import create_random_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..glsl import ShaderCompiler
from ..signals.signals import (
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
)
from .cppn_base import (
    CPPNSubstrateBase,
    _clamp_rgb,
    _compute_network_stats,
    _load_neat_config,
    normalize_to_bipolar,
    query_neat_network,
)
from .protocol import OutputType


class SingleCPPNSubstrate(CPPNSubstrateBase):
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
        self.config = _load_neat_config(
            neat_config_path,
            evolution_config.NEAT_CONFIG_PATH,
            VISUAL_INPUTS,
            VISUAL_OUTPUTS,
            "visual",
        )
        self._population = neat.Population(self.config)
        self.compiler = ShaderCompiler(
            VISUAL_INPUTS, None, VISUAL_DERIVED_INPUTS, color_mode=color_mode
        )

    def create_random(self, key: int = 0) -> neat.DefaultGenome:
        return create_random_genome(self.config, genome_id=key)

    def mutate(self, ind: neat.DefaultGenome, key: int) -> neat.DefaultGenome:
        child = mutate_genome(ind, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def crossover(
        self, a: neat.DefaultGenome, b: neat.DefaultGenome, key: int
    ) -> neat.DefaultGenome:
        child = crossover_genomes(a, b, self.config)
        child.key = key  # type: ignore[assignment]
        return child

    def _compile(self, compiler: Any, ind: neat.DefaultGenome) -> str | None:
        return compiler.compile_to_glsl(ind, self.config)

    def query_rgb(
        self, ind: neat.DefaultGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = query_neat_network(
            ind, self.config, VISUAL_INPUTS, VISUAL_DERIVED_INPUTS, inputs
        )
        return _clamp_rgb(out)

    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        return {
            **base,
            "x": x,
            "y": y,
            VISUAL_TIME_INPUT_NAME: time * 2.0 - 1.0,
        }

    def get_base_inputs_for_render(self) -> dict[str, float]:
        base = default_inputs(VISUAL_INPUTS)
        base[VISUAL_TIME_INPUT_NAME] = normalize_to_bipolar(0.0)
        return base

    def to_json(self, ind: neat.DefaultGenome) -> dict[str, Any]:
        return genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> neat.DefaultGenome:
        return genome_from_json(data, self.config)

    def get_compile_stats(self, ind: neat.DefaultGenome) -> dict[str, Any] | None:
        return _compute_network_stats([("visual", ind, self.config)])

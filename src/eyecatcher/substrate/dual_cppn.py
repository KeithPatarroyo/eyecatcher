"""
Dual-CPPN substrate: visual + time signal networks (current default).
"""

from __future__ import annotations

from typing import Any

from ..algorithm import config as evolution_config
from ..algorithm.engine import CPPNEngine
from ..genome import (
    DualGenome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from ..glsl import ShaderCompiler
from .protocol import OutputType, SubstrateOutput


class DualCPPNSubstrate:
    """
    Substrate that wraps the current dual-CPPN (visual + time) setup.
    Individual = DualGenome; output = shader.
    """

    id = "dual_cppn"
    output_type: OutputType = "shader"

    def __init__(
        self,
        neat_config_path: str | None = None,
        time_config_path: str | None = None,
        color_mode: str = "hsv",
        **kwargs: Any,
    ) -> None:
        neat_config_path = neat_config_path or evolution_config.NEAT_CONFIG_PATH
        time_config_path = time_config_path or evolution_config.NEAT_TIME_CONFIG_PATH
        # kwargs may contain preset keys (e.g. population_size) ignored here
        self.engine = CPPNEngine(neat_config_path, time_config_path)
        self.engine.create_population()
        self.compiler = ShaderCompiler(color_mode=color_mode)

    def create_random(self, key: int = 0) -> DualGenome:
        return create_random_dual_genome(
            self.engine.config, self.engine.time_config, genome_id=key
        )

    def mutate(self, ind: DualGenome, key: int) -> DualGenome:
        return self.engine.mutate_dual_genome(ind, key)

    def crossover(self, a: DualGenome, b: DualGenome, key: int) -> DualGenome:
        return self.engine.crossover_dual_genomes(a, b, key)

    def evaluate(
        self, ind: DualGenome, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        """Return shader output for display (real-time path uses compile_to_shader)."""
        glsl = self.compile_to_shader(ind)
        out = SubstrateOutput("shader", glsl) if glsl else SubstrateOutput("shader", "")
        return out

    def compile_to_shader(self, ind: DualGenome) -> str | None:
        return self.compiler.compile_dual_to_glsl(
            ind, self.engine.config, self.engine.time_config
        )

    def to_json(self, ind: DualGenome) -> dict[str, Any]:
        return dual_genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> DualGenome:
        return dual_genome_from_json(data, self.engine.config, self.engine.time_config)

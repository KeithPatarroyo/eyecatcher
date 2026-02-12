"""
Single-CPPN substrate: visual network only (no time signal CPPN).

Individual = neat.DefaultGenome. Output = shader.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import neat
import numpy as np

from .. import get_root_dir
from ..algorithm import DEFAULT_RENDER_RESOLUTION
from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_single_genomes, mutate_single_genome
from ..evaluation.rendering import render_image
from ..genome.genome import create_random_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..glsl import ShaderCompiler
from ..signals.activation import register_custom_activations
from ..signals.signals import VISUAL_INPUTS, VISUAL_OUTPUTS
from ..signals.validation import validate_neat_config
from .protocol import OutputType, SubstrateOutput


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
        validate_neat_config(self.config, VISUAL_INPUTS, VISUAL_OUTPUTS, "visual")
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

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "glsl": f"pattern_{individual_id}.glsl",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: neat.DefaultGenome, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        shader_code = self.compile_to_shader(ind) or ""
        img = render_image(ind, self.config, resolution=DEFAULT_RENDER_RESOLUTION)
        names = self.get_save_filenames(individual_id)
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["genome_json"]: json.dumps(genome_to_json(ind), indent=2).encode(
                "utf-8"
            ),
        }

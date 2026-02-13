"""
Single-CPPN substrate: visual network only (no time signal CPPN).

Individual = neat.DefaultGenome. Output = shader.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import neat
import numpy as np

from ..algorithm import DEFAULT_RENDER_RESOLUTION
from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_single_genomes, mutate_single_genome
from ..genome.genome import create_random_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..glsl import ShaderCompiler
from ..lib.math_utils import normalize_to_bipolar
from ..signals.signals import (
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
    get_default_signal_values,
)
from .cppn_base import (
    _load_neat_config,
    base_evaluate,
    compile_with_color_mode,
    query_neat_network,
    render_pixel_grid,
)
from .protocol import OutputType, SubstrateOutput


class SingleCPPNSubstrate:
    """
    Substrate with a single visual CPPN (no time signal network).
    Individual = neat.DefaultGenome; output = shader.
    """

    id = "single_cppn"
    output_type: OutputType = "shader"

    @classmethod
    def get_frontend_metadata(cls) -> dict:
        return {
            "hasSignalControls": False,
            "genomeKeys": ["visual"],
            "excludeKeys": ["time_signal"],
            "capabilities": {
                "save": True,
                "network": False,
                "timeOutput": False,
                "adjustWeight": False,
            },
        }

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
        return base_evaluate(lambda i: self.compile_to_shader(i), ind)

    def compile_to_shader(
        self, ind: neat.DefaultGenome, color_mode: str | None = None
    ) -> str | None:
        return compile_with_color_mode(
            self.compiler,
            ind,
            color_mode,
            lambda c, i, cfg: c.compile_to_glsl(i, cfg),
            ind,
            self.config,
        )

    def _query_visual_rgb(
        self, ind: neat.DefaultGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = query_neat_network(
            ind, self.config, VISUAL_INPUTS, VISUAL_DERIVED_INPUTS, inputs
        )
        r = max(0.0, min(1.0, (out[0] + 1.0) / 2.0))
        g = max(0.0, min(1.0, (out[1] + 1.0) / 2.0))
        b = max(0.0, min(1.0, (out[2] + 1.0) / 2.0))
        return r, g, b

    def sample_rgb(
        self,
        ind: neat.DefaultGenome,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        samples = []
        sigs = get_default_signal_values(time)
        for x, y in coords:
            inputs = {"x": x, "y": y, VISUAL_TIME_INPUT_NAME: time * 2.0 - 1.0, **sigs}
            r, g, b = self._query_visual_rgb(ind, inputs)
            samples.append([r, g, b])
        return samples

    def render_to_image(
        self,
        ind: neat.DefaultGenome,
        resolution: int | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        if resolution is None:
            resolution = DEFAULT_RENDER_RESOLUTION
        base = default_inputs(VISUAL_INPUTS)
        base[VISUAL_TIME_INPUT_NAME] = normalize_to_bipolar(0.0)
        return render_pixel_grid(
            resolution, base, lambda inputs: self._query_visual_rgb(ind, inputs)
        )

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
        img = self.render_to_image(ind, resolution=DEFAULT_RENDER_RESOLUTION)
        names = self.get_save_filenames(individual_id)
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["genome_json"]: json.dumps(genome_to_json(ind), indent=2).encode(
                "utf-8"
            ),
        }

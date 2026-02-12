"""
Dual-CPPN substrate: visual + time signal networks (current default).
"""

from __future__ import annotations

import io
import json
import pickle
from typing import Any, Callable

import numpy as np

from ..algorithm import DEFAULT_RENDER_RESOLUTION
from ..algorithm import config as evolution_config
from ..algorithm.engine import CPPNEngine
from ..evaluation import dual_genome_network_stats
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

    def get_compile_stats(self, ind: DualGenome) -> dict[str, Any] | None:
        """Return per-network node/connection counts for compile response."""
        return dual_genome_network_stats(ind)

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        return {
            "png": f"pattern_{individual_id}.png",
            "glsl": f"pattern_{individual_id}.glsl",
            "bundle_json": f"pattern_{individual_id}_bundle.json",
            "genome_json": f"genome_{individual_id}.json",
            "pkl": f"genome_{individual_id}.pkl",
            "network_pdf": f"genome_{individual_id}_network.pdf",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: DualGenome, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] = kwargs.get("to_png_bytes")
        visualize: bool = kwargs.get("visualize", True)
        if not callable(to_png_bytes):
            return {}
        shader_code = self.compile_to_shader(ind) or ""
        stats = self.get_compile_stats(ind) or {}
        bundle = {
            "shader": shader_code,
            "metadata": {
                "type": self.id,
                "visual": {
                    "num_nodes": stats.get("visual_nodes", 0),
                    "num_connections": stats.get("visual_connections", 0),
                },
                "time_signal": {
                    "num_nodes": stats.get("time_nodes", 0),
                    "num_connections": stats.get("time_connections", 0),
                },
                "fitness": ind.fitness,
            },
        }
        names = self.get_save_filenames(individual_id)
        img = self.engine.render_dual_image(ind, resolution=DEFAULT_RENDER_RESOLUTION)
        pkl_buffer = io.BytesIO()
        pickle.dump(
            {"visual": ind.visual, "time_signal": ind.time_signal, "key": ind.key},
            pkl_buffer,
        )
        assets = {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["bundle_json"]: json.dumps(bundle, indent=2).encode("utf-8"),
            names["genome_json"]: json.dumps(dual_genome_to_json(ind), indent=2).encode(
                "utf-8"
            ),
            names["pkl"]: pkl_buffer.getvalue(),
        }
        if visualize:
            from ..evaluation.genome_visualizer import render_genome_network_pdf

            pdf_buffer = io.BytesIO()
            render_genome_network_pdf(ind.visual, self.engine.config, pdf_buffer)
            assets[names["network_pdf"]] = pdf_buffer.getvalue()
        return assets

    def get_capabilities(self) -> dict[str, bool]:
        return {
            "save": True,
            "network": True,
            "time_output": True,
            "adjust_weight": True,
        }

"""
Dual-CPPN substrate: visual + time signal networks (current default).
"""

from __future__ import annotations

import io
import json
import os
import pickle
from typing import Any, Callable

import neat
import numpy as np

from .. import get_root_dir
from ..algorithm import DEFAULT_RENDER_RESOLUTION
from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_dual_genomes, mutate_dual_genome
from ..evaluation import (
    dual_genome_network_stats,
    extract_network_data,
    parse_network_node_id,
)
from ..evaluation.rendering import render_dual_image
from ..genome import (
    DualGenome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from ..glsl import ShaderCompiler
from ..signals.activation import register_custom_activations
from ..signals.signals import TIME_INPUTS, TIME_OUTPUTS, VISUAL_INPUTS, VISUAL_OUTPUTS
from ..signals.validation import validate_neat_config
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
        root = get_root_dir()
        if not os.path.isabs(neat_config_path):
            neat_config_path = os.path.join(root, neat_config_path)
        if not os.path.isabs(time_config_path):
            time_config_path = os.path.join(root, time_config_path)

        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            neat_config_path,
        )
        register_custom_activations(self.config)
        self.time_config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            time_config_path,
        )
        register_custom_activations(self.time_config)
        validate_neat_config(self.config, VISUAL_INPUTS, VISUAL_OUTPUTS, "visual")
        validate_neat_config(self.time_config, TIME_INPUTS, TIME_OUTPUTS, "time")

        self._population = neat.Population(self.config)
        self._time_population = neat.Population(self.time_config)
        self.population = self._population
        self.time_population = self._time_population
        self.compiler = ShaderCompiler(color_mode=color_mode)

    def create_random(self, key: int = 0) -> DualGenome:
        return create_random_dual_genome(self.config, self.time_config, genome_id=key)

    def mutate(self, ind: DualGenome, key: int) -> DualGenome:
        return mutate_dual_genome(ind, self.config, self.time_config, key)

    def crossover(self, a: DualGenome, b: DualGenome, key: int) -> DualGenome:
        return crossover_dual_genomes(a, b, self.config, self.time_config, key)

    def evaluate(
        self, ind: DualGenome, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        """Return shader output for display (real-time path uses compile_to_shader)."""
        glsl = self.compile_to_shader(ind)
        out = SubstrateOutput("shader", glsl) if glsl else SubstrateOutput("shader", "")
        return out

    def compile_to_shader(self, ind: DualGenome) -> str | None:
        return self.compiler.compile_dual_to_glsl(ind, self.config, self.time_config)

    def to_json(self, ind: DualGenome) -> dict[str, Any]:
        return dual_genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> DualGenome:
        return dual_genome_from_json(data, self.config, self.time_config)

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
        img = render_dual_image(
            ind, self.config, self.time_config, resolution=DEFAULT_RENDER_RESOLUTION
        )
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
            render_genome_network_pdf(ind.visual, self.config, pdf_buffer)
            assets[names["network_pdf"]] = pdf_buffer.getvalue()
        return assets

    def get_capabilities(self) -> dict[str, bool]:
        return {
            "save": True,
            "network": True,
            "time_output": True,
            "adjust_weight": True,
        }

    def query_time_output(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> dict[str, Any] | None:
        from ..evaluation.query import query_time_signal

        response_inputs = {}
        time_inputs = {}
        for s in TIME_INPUTS:
            raw_val = inputs.get(s.id)
            if raw_val is None and s.id == "raw_time":
                raw_val = inputs.get("time")
            val = float(raw_val if raw_val is not None else s.default)
            time_inputs[s.id] = val * 2.0 - 1.0
            response_inputs[s.id] = val
        out = query_time_signal(ind.time_signal, self.time_config, time_inputs)
        return {"timeOutput": out, "inputs": response_inputs}

    def get_network_data(self, ind: DualGenome) -> dict[str, Any] | None:
        all_nodes = []
        all_connections = []
        if ind.visual:
            nodes, conns = extract_network_data(ind.visual, "visual", self.config)
            all_nodes.extend(nodes)
            all_connections.extend(conns)
        if ind.time_signal:
            nodes, conns = extract_network_data(
                ind.time_signal, "time", self.time_config
            )
            all_nodes.extend(nodes)
            all_connections.extend(conns)
        return {"nodes": all_nodes, "connections": all_connections}

    def adjust_weight(
        self,
        ind: DualGenome,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        genome = ind.visual if network == "visual" else ind.time_signal
        try:
            source_id = parse_network_node_id(source)
            target_id = parse_network_node_id(target)
        except (ValueError, IndexError):
            return None
        conn_key = (source_id, target_id)
        if conn_key not in genome.connections:
            return None
        genome.connections[conn_key].weight = weight
        shader_code = self.compile_to_shader(ind) or ""
        return {"shader": shader_code, "genome": self.to_json(ind)}

"""
Dual-CPPN representation: visual + time signal networks (current default).
"""

from __future__ import annotations

import io
import json
import pickle
from typing import Any, Callable

import neat
import numpy as np

from ..experiment import NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH
from ..genome.dual import (
    DualGenome,
    create_random_dual_genome,
    crossover_dual_genomes,
    dual_genome_from_json,
    dual_genome_to_json,
    mutate_dual_genome,
)
from ..glsl import ShaderCompiler
from ..inspection import extract_network_data, parse_network_node_id
from ..signals.registry import (
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
    parse_time_inputs,
)
from .cppn_base import (
    CPPNRepresentationBase,
    _clamp_rgb,
    _compute_network_stats,
    _load_neat_config,
    query_neat_network,
)
from .protocol import OutputType


class DualCPPNRepresentation(CPPNRepresentationBase):
    """
    Representation that wraps the current dual-CPPN (visual + time) setup.
    Individual = DualGenome; output = shader.
    """

    id = "dual_cppn"
    output_type: OutputType = "shader"

    frontend_metadata = {
        "hasSignalControls": True,
        "genomeKeys": ["visual", "time_signal"],
    }

    def __init__(
        self,
        neat_config_path: str | None = None,
        time_config_path: str | None = None,
        color_mode: str = "hsv",
        **kwargs: Any,
    ) -> None:
        self.config = _load_neat_config(
            neat_config_path,
            NEAT_CONFIG_PATH,
            VISUAL_INPUTS,
            VISUAL_OUTPUTS,
            "visual",
        )
        self.time_config = _load_neat_config(
            time_config_path,
            NEAT_TIME_CONFIG_PATH,
            TIME_INPUTS,
            TIME_OUTPUTS,
            "time",
        )
        self._population = neat.Population(self.config)
        self._time_population = neat.Population(self.time_config)
        self.population = self._population
        self.time_population = self._time_population
        self.compiler = ShaderCompiler(
            VISUAL_INPUTS, TIME_INPUTS, VISUAL_DERIVED_INPUTS, color_mode=color_mode
        )

    def create_random(self, key: int = 0) -> DualGenome:
        return create_random_dual_genome(self.config, self.time_config, genome_id=key)

    def mutate(self, ind: DualGenome, key: int) -> DualGenome:
        return mutate_dual_genome(ind, self.config, self.time_config, key)

    def crossover(self, a: DualGenome, b: DualGenome, key: int) -> DualGenome:
        return crossover_dual_genomes(a, b, self.config, self.time_config, key)

    def _compile(self, compiler: Any, ind: DualGenome) -> str | None:
        return compiler.compile(ind, self.config, self.time_config)

    def _query_time_signal(
        self, time_genome: neat.DefaultGenome, inputs: dict[str, float]
    ) -> float:
        out = query_neat_network(time_genome, self.time_config, TIME_INPUTS, [], inputs)
        return max(-1.0, min(1.0, out[0]))

    def _query_visual_rgb(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = query_neat_network(
            ind.visual,
            self.config,
            VISUAL_INPUTS,
            VISUAL_DERIVED_INPUTS,
            inputs,
        )
        return _clamp_rgb(out)

    def query_rgb(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        modified_time = self._query_time_signal(ind.time_signal, inputs)
        visual_inputs = {
            **inputs,
            VISUAL_TIME_INPUT_NAME: modified_time,
        }
        return self._query_visual_rgb(ind, visual_inputs)

    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        return {**base, "x": x, "y": y}

    def get_base_inputs_for_render(self) -> dict[str, float]:
        return default_inputs(TIME_INPUTS)

    def to_json(self, ind: DualGenome) -> dict[str, Any]:
        return dual_genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> DualGenome:
        return dual_genome_from_json(data, self.config, self.time_config)

    def get_compile_stats(self, ind: DualGenome) -> dict[str, Any] | None:
        return _compute_network_stats(
            [
                ("visual", ind.visual, self.config),
                ("time", ind.time_signal, self.time_config),
            ]
        )

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        base = super().get_save_filenames(individual_id)
        base["bundle_json"] = f"pattern_{individual_id}_bundle.json"
        base["pkl"] = f"genome_{individual_id}.pkl"
        base["network_pdf"] = f"genome_{individual_id}_network.pdf"
        return base

    def build_save_assets(
        self, ind: DualGenome, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        to_png_bytes: Callable[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        visualize: bool = kwargs.get("visualize", True)
        if not callable(to_png_bytes):
            return {}
        assets = super().build_save_assets(ind, individual_id, **kwargs)
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
        pkl_buffer = io.BytesIO()
        pickle.dump(
            {"visual": ind.visual, "time_signal": ind.time_signal, "key": ind.key},
            pkl_buffer,
        )
        assets[names["bundle_json"]] = json.dumps(bundle, indent=2).encode("utf-8")
        assets[names["pkl"]] = pkl_buffer.getvalue()
        if visualize:
            from ..inspection.genome_visualizer import render_genome_network_pdf

            pdf_buffer = io.BytesIO()
            render_genome_network_pdf(ind.visual, self.config, pdf_buffer)
            assets[names["network_pdf"]] = pdf_buffer.getvalue()
        return assets

    def query_time_output(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> dict[str, Any] | None:
        response_inputs = parse_time_inputs(inputs, bipolar=False)
        time_inputs = parse_time_inputs(inputs, bipolar=True)
        out = self._query_time_signal(ind.time_signal, time_inputs)
        return {"timeOutput": out, "inputs": response_inputs}

    def get_network_data(self, ind: DualGenome) -> dict[str, Any] | None:
        all_nodes = []
        all_connections = []
        if ind.visual:
            nodes, conns = extract_network_data(
                ind.visual, "visual", self.config, x_offset=0
            )
            all_nodes.extend(nodes)
            all_connections.extend(conns)
        if ind.time_signal:
            nodes, conns = extract_network_data(
                ind.time_signal, "time", self.time_config, x_offset=1000
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
        return {"shader": shader_code, "individual": self.to_json(ind)}

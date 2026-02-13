"""
Dual-CPPN substrate: visual + time signal networks (current default).
"""

from __future__ import annotations

import io
import json
import pickle
from typing import Any, Callable

import neat
import numpy as np

from ..algorithm import DEFAULT_RENDER_RESOLUTION
from ..algorithm import config as evolution_config
from ..algorithm.operators import crossover_dual_genomes, mutate_dual_genome
from ..evaluation import extract_network_data, parse_network_node_id
from ..genome import (
    DualGenome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from ..glsl import ShaderCompiler
from ..signals.signals import (
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_DERIVED_INPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
    VISUAL_TIME_INPUT_NAME,
    default_inputs,
    get_default_signal_values,
    parse_time_inputs,
)
from .cppn_base import (
    _load_neat_config,
    base_evaluate,
    compile_with_color_mode,
    query_neat_network,
    render_pixel_grid,
)
from .protocol import OutputType, SubstrateOutput


class DualCPPNSubstrate:
    """
    Substrate that wraps the current dual-CPPN (visual + time) setup.
    Individual = DualGenome; output = shader.
    """

    id = "dual_cppn"
    output_type: OutputType = "shader"

    @classmethod
    def get_frontend_metadata(cls) -> dict:
        return {
            "hasSignalControls": True,
            "genomeKeys": ["visual", "time_signal"],
            "capabilities": {
                "save": True,
                "network": True,
                "timeOutput": True,
                "adjustWeight": True,
            },
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
            evolution_config.NEAT_CONFIG_PATH,
            VISUAL_INPUTS,
            VISUAL_OUTPUTS,
            "visual",
        )
        self.time_config = _load_neat_config(
            time_config_path,
            evolution_config.NEAT_TIME_CONFIG_PATH,
            TIME_INPUTS,
            TIME_OUTPUTS,
            "time",
        )
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
        return base_evaluate(lambda i: self.compile_to_shader(i), ind)

    def compile_to_shader(
        self, ind: DualGenome, color_mode: str | None = None
    ) -> str | None:
        return compile_with_color_mode(
            self.compiler,
            ind,
            color_mode,
            lambda c, i, cfg, tc: c.compile_dual_to_glsl(i, cfg, tc),
            ind,
            self.config,
            self.time_config,
        )

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
        r = max(0.0, min(1.0, (out[0] + 1.0) / 2.0))
        g = max(0.0, min(1.0, (out[1] + 1.0) / 2.0))
        b = max(0.0, min(1.0, (out[2] + 1.0) / 2.0))
        return r, g, b

    def _query_dual_cppn(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        modified_time = self._query_time_signal(ind.time_signal, inputs)
        visual_inputs = {**inputs, VISUAL_TIME_INPUT_NAME: modified_time}
        return self._query_visual_rgb(ind, visual_inputs)

    def sample_rgb(
        self,
        ind: DualGenome,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        samples = []
        base = get_default_signal_values(time)
        for x, y in coords:
            inputs = {"x": x, "y": y, **base}
            r, g, b = self._query_dual_cppn(ind, inputs)
            samples.append([r, g, b])
        return samples

    def render_to_image(
        self,
        ind: DualGenome,
        resolution: int | None = None,
        extra_inputs: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        if resolution is None:
            resolution = DEFAULT_RENDER_RESOLUTION
        base = default_inputs(TIME_INPUTS)
        if extra_inputs:
            base.update(extra_inputs)
        return render_pixel_grid(
            resolution,
            base,
            lambda inputs: self._query_dual_cppn(ind, inputs),
        )

    def to_json(self, ind: DualGenome) -> dict[str, Any]:
        return dual_genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> DualGenome:
        return dual_genome_from_json(data, self.config, self.time_config)

    def get_compile_stats(self, ind: DualGenome) -> dict[str, Any] | None:
        v_nodes = len(ind.visual.nodes)
        v_conns = len([c for c in ind.visual.connections.values() if c.enabled])
        t_nodes = len(ind.time_signal.nodes)
        t_conns = len([c for c in ind.time_signal.connections.values() if c.enabled])
        return {
            "visual_nodes": v_nodes,
            "visual_connections": v_conns,
            "time_nodes": t_nodes,
            "time_connections": t_conns,
        }

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
        img = self.render_to_image(ind, resolution=DEFAULT_RENDER_RESOLUTION)
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
        response_inputs = parse_time_inputs(inputs, bipolar=False)
        time_inputs = parse_time_inputs(inputs, bipolar=True)
        out = self._query_time_signal(ind.time_signal, time_inputs)
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

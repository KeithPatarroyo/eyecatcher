"""
Dual-CPPN representation: visual + time signal networks (current default).

Expression and signal translation are delegated to NeatSocket instances.
Evolution (populations, mutation, crossover) is owned by the representation.
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
from ..inspection import parse_network_node_id
from ..signals import catalog
from ..signals.registry import parse_time_inputs
from ..signals.spec import SignalSpec
from .cppn_base import CPPNRepresentationBase, _clamp_rgb
from .protocol import OutputType
from .sockets import NeatSocket


class DualCPPNRepresentation(CPPNRepresentationBase):
    """
    Representation that wraps the current dual-CPPN (visual + time) setup.
    Individual = DualGenome; output = shader.

    Sockets handle expression (signal -> network query -> output).
    Representation handles evolution (populations, mutation, crossover).
    """

    id = "dual_cppn"
    output_type: OutputType = "shader"
    frontend_metadata = {
        "hasSignalControls": True,
        "genomeKeys": ["visual", "time_signal"],
        "adapterFactory": "cppn",
    }

    def __init__(
        self,
        neat_config_path: str | None = None,
        time_config_path: str | None = None,
        color_mode: str = "hsv",
        **kwargs: Any,
    ) -> None:
        self.visual = NeatSocket(
            "visual",
            inputs=catalog.DUAL_CPPN_VISUAL_INPUTS,
            outputs=catalog.RGB_OUTPUTS,
            derived=(catalog.DISTANCE,),
            config_path=neat_config_path or NEAT_CONFIG_PATH,
        )
        self.time = NeatSocket(
            "time",
            inputs=catalog.DUAL_CPPN_TIME_INPUTS,
            outputs=catalog.TIME_OUTPUT,
            config_path=time_config_path or NEAT_TIME_CONFIG_PATH,
        )
        self.signal_spec = SignalSpec(
            sockets=(self.visual, self.time),
            outputs=catalog.RGB_OUTPUTS,
            substitutions={"time": "timeFromNetwork"},
        )
        super().__init__(color_mode=color_mode)
        self.time_config = self.time.config
        self._time_population = neat.Population(self.time_config)
        self.population = self._population
        self.time_population = self._time_population

    # -- Evolution (representation concern) --

    def create_random(self, key: int = 0) -> DualGenome:
        return create_random_dual_genome(self.config, self.time_config, genome_id=key)

    def mutate(self, ind: DualGenome, key: int) -> DualGenome:
        return mutate_dual_genome(ind, self.config, self.time_config, key)

    def crossover(self, a: DualGenome, b: DualGenome, key: int) -> DualGenome:
        return crossover_dual_genomes(a, b, self.config, self.time_config, key)

    # -- Expression (delegated to sockets) --

    def _compile(self, compiler: Any, ind: DualGenome) -> str | None:
        return compiler.compile(
            ind.visual, self.config, ind.time_signal, self.time_config
        )

    def _query_time_signal(
        self, time_genome: neat.DefaultGenome, inputs: dict[str, float]
    ) -> float:
        out = self.time.query(time_genome, inputs)
        return max(-1.0, min(1.0, out[0]))

    def _query_visual_rgb(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = self.visual.query(ind.visual, inputs)
        return _clamp_rgb(out)

    def query_rgb(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        modified_time = self._query_time_signal(ind.time_signal, inputs)
        visual_inputs = {
            **inputs,
            catalog.time.id: modified_time,
        }
        return self._query_visual_rgb(ind, visual_inputs)

    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        return {**base, "x": x, "y": y}

    def get_base_inputs_for_render(self) -> dict[str, float]:
        return self.time.default_values()

    # -- Serialization --

    def to_json(self, ind: DualGenome) -> dict[str, Any]:
        return dual_genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> DualGenome:
        return dual_genome_from_json(data, self.config, self.time_config)

    def get_network_types(self) -> tuple[str, ...]:
        return ("visual", "time_signal")

    def get_neat_pop_size(self) -> int | None:
        return getattr(self.config, "pop_size", None)

    # -- Inspection (sockets know the structure of the individual) --

    def get_compile_stats(self, ind: DualGenome) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        stats.update(self.visual.network_stats(ind.visual))
        stats.update(self.time.network_stats(ind.time_signal))
        return stats

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
        stats = self.get_compile_stats(ind)
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
            pdf_buffer = io.BytesIO()
            self.visual.render_network_pdf(ind.visual, pdf_buffer)
            assets[names["network_pdf"]] = pdf_buffer.getvalue()
        return assets

    def query_time_output(
        self, ind: DualGenome, inputs: dict[str, float]
    ) -> dict[str, Any] | None:
        time_signals = list(self.time.inputs)
        response_inputs = parse_time_inputs(inputs, time_signals, bipolar=False)
        time_inputs = parse_time_inputs(inputs, time_signals, bipolar=True)
        out = self._query_time_signal(ind.time_signal, time_inputs)
        return {"timeOutput": out, "inputs": response_inputs}

    def get_network_data(self, ind: DualGenome) -> dict[str, Any] | None:
        all_nodes: list[dict[str, Any]] = []
        all_connections: list[dict[str, Any]] = []
        if ind.visual:
            nodes, conns = self.visual.extract_network_data(ind.visual, x_offset=0)
            all_nodes.extend(nodes)
            all_connections.extend(conns)
        if ind.time_signal:
            nodes, conns = self.time.extract_network_data(
                ind.time_signal, x_offset=1000
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

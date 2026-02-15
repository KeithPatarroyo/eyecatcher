"""
Single-CPPN representation: visual network only (no time signal CPPN).

Expression and signal translation are delegated to a NeatSocket.
Evolution (population, mutation, crossover) is owned by the representation.
"""

from __future__ import annotations

from typing import Any

import neat

from ..experiment import NEAT_CONFIG_PATH
from ..genome import create_random_genome
from ..genome.operators import crossover_genomes, mutate_genome
from ..genome.serialization import genome_from_json, genome_to_json
from ..signals import catalog
from ..signals.spec import SignalSpec
from .cppn_base import CPPNRepresentationBase, _clamp_rgb, normalize_to_bipolar
from .protocol import Phenotype
from .sockets import NeatSocket


class SingleCPPNRepresentation(CPPNRepresentationBase):
    """
    Representation with a single visual CPPN (no time signal network).
    Individual = neat.DefaultGenome; output = shader.

    Socket handles expression (signal -> network query -> output).
    Representation handles evolution (population, mutation, crossover).
    """

    id = "single_cppn"
    frontend_metadata = {
        "hasSignalControls": False,
        "genomeKeys": ["visual"],
        "excludeKeys": ["time_signal"],
    }

    phenotype = Phenotype(
        substrate="shader",
        meta_template="Nodes: {nodes} | Connections: {connections}",
    )

    def __init__(
        self,
        neat_config_path: str | None = None,
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
        self.signal_spec = SignalSpec(
            sockets=(self.visual,),
            outputs=catalog.RGB_OUTPUTS,
        )
        super().__init__(color_mode=color_mode)

    # -- Evolution (representation concern) --

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

    # -- Expression (delegated to socket) --

    def _compile(self, compiler: Any, ind: neat.DefaultGenome) -> str | None:
        return compiler.compile(ind, self.config)

    def query_rgb(
        self, ind: neat.DefaultGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = self.visual.query(ind, inputs)
        return _clamp_rgb(out)

    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        return {
            **base,
            "x": x,
            "y": y,
            catalog.time.id: time * 2.0 - 1.0,
        }

    def get_base_inputs_for_render(self) -> dict[str, float]:
        base = self.visual.default_values()
        base[catalog.time.id] = normalize_to_bipolar(0.0)
        return base

    # -- Serialization --

    def to_json(self, ind: neat.DefaultGenome) -> dict[str, Any]:
        return genome_to_json(ind)

    def from_json(self, data: dict[str, Any]) -> neat.DefaultGenome:
        return genome_from_json(data, self.config)

    def get_network_types(self) -> tuple[str, ...]:
        return ("visual",)

    def get_neat_pop_size(self) -> int | None:
        return getattr(self.config, "pop_size", None)

    # -- Inspection (socket knows the structure) --

    def get_compile_stats(self, ind: neat.DefaultGenome) -> dict[str, Any]:
        return self.visual.network_stats(ind)

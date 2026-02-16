"""
Single-CPPN representation: visual network only (no time signal CPPN).

Expression and signal translation are delegated to a NeatReceptor.
Evolution (population, mutation, crossover) from FieldRepresentationBase/NeatEvolvable.
"""

from __future__ import annotations

from typing import Any

import neat

from .. import experiment
from ..signals import catalog
from ..signals.sensory_system import SensorySystem
from .field_base import (
    FieldRepresentationBase,
    _clamp_rgb,
    normalize_to_bipolar,
)
from .mixins import NetworkInspectable
from .protocol import Phenotype, Substrate
from .receptors import NeatReceptor


class SingleCPPNRepresentation(NetworkInspectable, FieldRepresentationBase):
    """
    Representation with a single visual CPPN (no time signal network).
    Individual = neat.DefaultGenome; output = rule.

    Receptor handles expression (signal -> network query -> output).
    Representation handles evolution (population, mutation, crossover).
    """

    id = "single_cppn"
    frontend_metadata = {
        "hasSignalControls": False,
        "genomeKeys": ["visual"],
        "excludeKeys": ["time_signal"],
    }

    phenotype = Phenotype(
        substrate=Substrate(type="field"),
        meta_template="Nodes: {nodes} | Connections: {connections}",
    )

    def __init__(
        self,
        neat_config_path: str | None = None,
        color_mode: str = "hsv",
        **kwargs: Any,
    ) -> None:
        self.visual = NeatReceptor(
            "visual",
            inputs=catalog.DUAL_CPPN_VISUAL_INPUTS,
            outputs=catalog.RGB_OUTPUTS,
            derived=(catalog.DISTANCE,),
            config_path=neat_config_path or experiment.NEAT_CONFIG_PATH,
            role="primary",
        )
        self.sensory_system = SensorySystem(
            receptors=(self.visual,),
            outputs=catalog.RGB_OUTPUTS,
        )
        super().__init__(color_mode=color_mode)

    @property
    def receptors(self) -> tuple[NeatReceptor, ...]:
        """NetworkInspectable: single visual receptor."""
        return (self.visual,)

    # -- Expression (delegated to receptor) --

    def _compile_contributions(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        return {"visual": self.visual.compile(genome)}

    def query_rgb(
        self, genome: neat.DefaultGenome, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        out = self.visual.query(genome, inputs)
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

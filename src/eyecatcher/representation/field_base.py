"""
Field-substrate representation base.

Shared develop, express, sample, render, save for SingleCPPN and DualCPPN.
Expression and signal translation are delegated to NeatReceptor instances.
Subclasses set self.visual (and optionally self.time), self.sensory_system,
then call super().__init__(color_mode=...).
"""

from __future__ import annotations

import json
from abc import abstractmethod
from collections.abc import Callable as Cb
from typing import Any

import neat
import numpy as np

from .. import experiment
from ..glsl import RuleAssembler
from ..signals.registry import get_default_signal_values
from .base import RepresentationBase
from .mixins import NeatEvolvable, Samplable, Saveable
from .protocol import RepresentationOutput


def normalize_to_bipolar(val: float) -> float:
    """Map value from [0, 1] to [-1, 1]."""
    return val * 2.0 - 1.0


def _clamp_rgb(out: list[float]) -> tuple[float, float, float]:
    """Convert three bipolar outputs to 0–1 RGB."""
    r = max(0.0, min(1.0, (out[0] + 1.0) / 2.0))
    g = max(0.0, min(1.0, (out[1] + 1.0) / 2.0))
    b = max(0.0, min(1.0, (out[2] + 1.0) / 2.0))
    return r, g, b


def _rgb_uint8(r: float, g: float, b: float) -> list[int]:
    """Convert 0–1 RGB floats to uint8 list for image pixel."""
    return [int(r * 255), int(g * 255), int(b * 255)]


def render_pixel_grid(
    resolution: int,
    base_inputs: dict,
    query_fn: Cb[[dict], tuple[float, float, float]],
) -> np.ndarray:
    """Fill (res, res, 3) image via query_fn per pixel (base_inputs + x, y)."""
    img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for i in range(resolution):
        for j in range(resolution):
            x = normalize_to_bipolar(i / resolution)
            y = normalize_to_bipolar(j / resolution)
            inputs = {**base_inputs, "x": x, "y": y}
            r, g, b = query_fn(inputs)
            img[j, i] = _rgb_uint8(r, g, b)
    return img


def base_express(
    develop_fn: Cb[[Any], str | None], genome: Any
) -> RepresentationOutput:
    """Wrap develop result in RepresentationOutput."""
    glsl = develop_fn(genome)
    return RepresentationOutput("field", glsl if glsl else "")


class FieldRepresentationBase(NeatEvolvable, Saveable, Samplable, RepresentationBase):
    """
    Shared base for field-substrate representations (SingleCPPN, DualCPPN).
    Subclasses set self.visual (and optionally self.time), self.sensory_system,
    then call super().__init__(color_mode=...). Subclasses implement
    query_rgb, _sample_inputs, get_base_inputs_for_render, _compile_contributions.
    DualCPPN overrides create_random, mutate, crossover, to_json, from_json.
    """

    def __init__(self, *, color_mode: str = "hsv") -> None:
        self.config = self.visual.config
        self._population = neat.Population(self.config)
        self.rule_assembler = RuleAssembler.from_sensory_system(
            self.sensory_system, color_mode=color_mode
        )

    @property
    def neat_config(self) -> neat.Config:
        """NeatEvolvable: NEAT config for primary (visual) genome."""
        return self.config

    @abstractmethod
    def query_rgb(
        self, genome: Any, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        """Return (r, g, b) in 0–1 for this genome and inputs."""
        ...

    @abstractmethod
    def _sample_inputs(
        self, x: float, y: float, time: float, base: dict[str, float]
    ) -> dict[str, float]:
        """Build input dict for one sample point."""
        ...

    @abstractmethod
    def get_base_inputs_for_render(self) -> dict[str, float]:
        """Base inputs for render_to_image (e.g. default_inputs for the network)."""
        ...

    @abstractmethod
    def _compile_contributions(self, genome: Any) -> dict[str, Any]:
        """Compile genome through receptors. Return dict with 'visual' and
        optionally 'time'.
        """
        ...

    def develop(self, genome: Any, color_mode: str | None = None) -> str | None:
        """Compile genome to rendering rule string via receptors and rule assembler."""
        assembler = self.rule_assembler
        if color_mode and color_mode != assembler.color_mode:
            assembler = assembler.with_color_mode(color_mode)
        contributions = self._compile_contributions(genome)
        return assembler.assemble(
            primary=contributions["visual"],
            modifier=contributions.get("time"),
        )

    def express(
        self, genome: Any, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Wrap develop in RepresentationOutput."""
        return base_express(lambda g: self.develop(g), genome)

    def sample_rgb(
        self,
        genome: Any,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        """Sample RGB at each (x, y) with shared time/signal base."""
        base = get_default_signal_values(self.sensory_system, time=time)
        return [
            list(self.query_rgb(genome, self._sample_inputs(x, y, time, base)))
            for x, y in coords
        ]

    def render_to_image(
        self,
        genome: Any,
        resolution: int | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        """Render genome to (resolution, resolution, 3) RGB image."""
        if resolution is None:
            resolution = experiment.DEFAULT_RENDER_RESOLUTION
        return render_pixel_grid(
            resolution,
            self.get_base_inputs_for_render(),
            lambda inputs: self.query_rgb(genome, inputs),
        )

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """Common filenames for save bundle; subclasses may override to add keys."""
        return {
            "png": f"pattern_{individual_id}.png",
            "glsl": f"pattern_{individual_id}.glsl",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, genome: Any, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """Common save assets (png, glsl, genome_json). Override to add more."""
        to_png_bytes: Cb[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        names = self.get_save_filenames(individual_id)
        rule_code = self.develop(genome) or ""
        res = experiment.DEFAULT_RENDER_RESOLUTION
        img = self.render_to_image(genome, resolution=res)
        json_bytes = json.dumps(self.to_json(genome), indent=2).encode("utf-8")
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: rule_code.encode("utf-8"),
            names["genome_json"]: json_bytes,
        }

    def serialize_output(
        self, output: RepresentationOutput, genome: Any = None
    ) -> dict[str, Any]:
        """Field output is rule string."""
        rule_str = output.data if isinstance(output.data, str) else ""
        return {"rule": rule_str}

    def has_temporal_signals(self) -> bool:
        """Field representations have time as an input."""
        return True

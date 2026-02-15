"""
Shared CPPN representation helpers: render utilities and CPPNRepresentationBase.

Expression and signal translation are delegated to NeatSocket instances.
CPPNRepresentationBase implements shared orchestration logic (compile, render,
sample, save) for SingleCPPNRepresentation and DualCPPNRepresentation.
"""

from __future__ import annotations

import json
from abc import abstractmethod
from collections.abc import Callable as Cb
from typing import Any

import neat
import numpy as np

from ..experiment.config import DEFAULT_RENDER_RESOLUTION
from ..glsl import ShaderCompiler
from ..signals.registry import get_default_signal_values
from .base import RepresentationBase
from .mixins import Samplable, Saveable
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
    return RepresentationOutput("shader", glsl if glsl else "")


def compile_with_color_mode(
    compiler: Any,
    genome: Any,
    color_mode: str | None,
    develop_fn: Cb[[Any, Any], str | None],
    *develop_args: Any,
) -> str | None:
    """Use one-off compiler if color_mode differs; else use given compiler."""
    if color_mode and color_mode != compiler.color_mode:
        alt = compiler.with_color_mode(color_mode)
        return develop_fn(alt, *develop_args)
    return develop_fn(compiler, *develop_args)


class CPPNRepresentationBase(Saveable, Samplable, RepresentationBase):
    """
    Shared base for single and dual CPPN representations.
    Subclasses set self.visual (and optionally self.time), self.signal_spec,
    then call super().__init__(color_mode=...). Subclasses implement
    query_rgb, _sample_inputs, get_base_inputs_for_render, _compile,
    to_json, from_json, create_random, mutate, crossover.
    """

    def __init__(self, *, color_mode: str = "hsv") -> None:
        self.config = self.visual.config
        self._population = neat.Population(self.config)
        self.compiler = ShaderCompiler.from_spec(
            self.signal_spec, color_mode=color_mode
        )

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
    def _compile(self, compiler: Any, genome: Any) -> str | None:
        """Compile genome to GLSL using the given compiler. Subclass-specific."""
        ...

    def develop(self, genome: Any, color_mode: str | None = None) -> str | None:
        """Compile genome to GLSL fragment shader string."""
        return compile_with_color_mode(
            self.compiler, genome, color_mode, self._compile, genome
        )

    @abstractmethod
    def to_json(self, genome: Any) -> dict[str, Any]:
        """Serialize genome to JSON-serializable dict."""
        ...

    @abstractmethod
    def from_json(self, data: dict[str, Any]) -> Any:
        """Deserialize individual from dict."""
        ...

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
        base = get_default_signal_values(self.signal_spec, time=time)
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
            resolution = DEFAULT_RENDER_RESOLUTION
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
        shader_code = self.develop(genome) or ""
        img = self.render_to_image(genome, resolution=DEFAULT_RENDER_RESOLUTION)
        json_bytes = json.dumps(self.to_json(genome), indent=2).encode("utf-8")
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["genome_json"]: json_bytes,
        }

    def serialize_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """CPPN output is shader string."""
        glsl = output.data if isinstance(output.data, str) else ""
        return {"shader": glsl}

    def has_temporal_signals(self) -> bool:
        """CPPN representations have time as an input."""
        return True

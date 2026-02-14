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

import numpy as np

from ..experiment.config import DEFAULT_RENDER_RESOLUTION
from ..signals.registry import get_default_signal_values
from .base import RepresentationBase
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


def base_express(compile_fn: Cb[[Any], str | None], ind: Any) -> RepresentationOutput:
    """Wrap compile_to_shader result in RepresentationOutput."""
    glsl = compile_fn(ind)
    return RepresentationOutput("shader", glsl if glsl else "")


def compile_with_color_mode(
    compiler: Any,
    ind: Any,
    color_mode: str | None,
    compile_fn: Cb[[Any, Any], str | None],
    *compile_args: Any,
) -> str | None:
    """Use one-off compiler if color_mode differs; else use given compiler."""
    if color_mode and color_mode != compiler.color_mode:
        alt = compiler.with_color_mode(color_mode)
        return compile_fn(alt, *compile_args)
    return compile_fn(compiler, *compile_args)


class CPPNRepresentationBase(RepresentationBase):
    """
    Shared base for single and dual CPPN representations.
    Subclasses implement query_rgb, _sample_inputs, get_base_inputs_for_render,
    _compile, to_json, from_json, create_random, mutate, crossover.
    """

    @abstractmethod
    def query_rgb(
        self, ind: Any, inputs: dict[str, float]
    ) -> tuple[float, float, float]:
        """Return (r, g, b) in 0–1 for this individual and inputs."""
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
    def _compile(self, compiler: Any, ind: Any) -> str | None:
        """Compile individual to GLSL using the given compiler. Subclass-specific."""
        ...

    def compile_to_shader(self, ind: Any, color_mode: str | None = None) -> str | None:
        """Compile individual to GLSL fragment shader string."""
        return compile_with_color_mode(
            self.compiler, ind, color_mode, self._compile, ind
        )

    @abstractmethod
    def to_json(self, ind: Any) -> dict[str, Any]:
        """Serialize individual to JSON-serializable dict."""
        ...

    @abstractmethod
    def from_json(self, data: dict[str, Any]) -> Any:
        """Deserialize individual from dict."""
        ...

    def express(
        self, ind: Any, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Wrap compile_to_shader in RepresentationOutput."""
        return base_express(lambda i: self.compile_to_shader(i), ind)

    def sample_rgb(
        self,
        ind: Any,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        """Sample RGB at each (x, y) with shared time/signal base."""
        base = get_default_signal_values(self.signal_spec, time=time)
        return [
            list(self.query_rgb(ind, self._sample_inputs(x, y, time, base)))
            for x, y in coords
        ]

    def render_to_image(
        self,
        ind: Any,
        resolution: int | None = None,
        **kwargs: Any,
    ) -> np.ndarray:
        """Render individual to (resolution, resolution, 3) RGB image."""
        if resolution is None:
            resolution = DEFAULT_RENDER_RESOLUTION
        return render_pixel_grid(
            resolution,
            self.get_base_inputs_for_render(),
            lambda inputs: self.query_rgb(ind, inputs),
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
        self, ind: Any, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """Common save assets (png, glsl, genome_json). Override to add more."""
        to_png_bytes: Cb[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        names = self.get_save_filenames(individual_id)
        shader_code = self.compile_to_shader(ind) or ""
        img = self.render_to_image(ind, resolution=DEFAULT_RENDER_RESOLUTION)
        json_bytes = json.dumps(self.to_json(ind), indent=2).encode("utf-8")
        return {
            names["png"]: to_png_bytes(img),
            names["glsl"]: shader_code.encode("utf-8"),
            names["genome_json"]: json_bytes,
        }

    def serialize_express_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """CPPN output is shader string."""
        glsl = output.data if isinstance(output.data, str) else ""
        return {"shader": glsl}

    def has_temporal_signals(self) -> bool:
        """CPPN representations have time as an input."""
        return True

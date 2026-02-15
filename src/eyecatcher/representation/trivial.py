"""
Minimal non-NEAT representation: template for custom representations (e.g. audio).

Genome = single float value (0–1) + key. One socket ties a signal to the "body part"
that expresses it (here, the solid-color display). express() uses both genome and
the socket's input signal. Copy this module when adding a custom representation
that does not use CPPNs (e.g. audio, custom nets).
"""

from __future__ import annotations

import base64
import io
import random
from typing import Any

import numpy as np

from ..signals import catalog
from ..signals.socket import Socket
from ..signals.spec import SignalSpec
from .base import RepresentationBase
from .mixins import GridAnalyzable
from .protocol import Phenotype, RepresentationOutput

SIZE = 16  # 16×16 grid for express output


class TrivialGenome:
    """Minimal genome: one value (0–1) and key (individual id)."""

    __slots__ = ("value", "key")

    def __init__(self, value: float, key: int = 0) -> None:
        self.value = float(value)
        self.key = key


def _rgb_to_png_base64(arr: np.ndarray) -> str:
    """Encode (H, W, 3) uint8 RGB as PNG base64 (no data URL prefix)."""
    from PIL import Image

    arr = np.asarray(arr)
    if arr.ndim != 3 or arr.shape[2] != 3:
        arr = np.stack([arr, arr, arr], axis=-1) if arr.ndim == 2 else arr
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class TrivialRepresentation(GridAnalyzable, RepresentationBase):
    """
    Minimal representation: one socket, one signal, one "body part" (the display).

    The socket ties the signal (e.g. raw_time) to the part that expresses it: the
    solid-color grid. express() combines genome value and socket input. Copy this
    pattern for custom representations (e.g. audio); see ca.py for a full example.
    """

    id = "trivial"
    frontend_metadata = {
        "hasSignalControls": True,
        "genomeKeys": ["value", "key"],
    }
    phenotype = Phenotype(substrate="grid")

    def __init__(self, **kwargs: Any) -> None:
        # One socket = one input target. Here the "display" part consumes raw_time.
        self.display = Socket(
            "display",
            inputs=(catalog.raw_time,),
            outputs=(),
            derived=(),
        )
        self.signal_spec = SignalSpec(sockets=(self.display,), outputs=())

    def create_random(self, key: int = 0) -> TrivialGenome:
        return TrivialGenome(value=random.random(), key=key)

    def mutate(self, genome: TrivialGenome, key: int) -> TrivialGenome:
        delta = (random.random() - 0.5) * 0.2
        return TrivialGenome(value=max(0.0, min(1.0, genome.value + delta)), key=key)

    def crossover(self, a: TrivialGenome, b: TrivialGenome, key: int) -> TrivialGenome:
        v = (a.value + b.value) / 2.0
        return TrivialGenome(value=v, key=key)

    def express(
        self, genome: TrivialGenome, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        # Genome value + socket signal: the "display" part expresses both.
        t = inputs.get("raw_time", 0.5)
        blend = genome.value * 0.6 + t * 0.4  # 0–1
        c = int(max(0, min(1, blend)) * 255)
        rgb = np.full((SIZE, SIZE, 3), c, dtype=np.uint8)
        return RepresentationOutput("grid", rgb)

    def to_json(self, genome: TrivialGenome) -> dict[str, Any]:
        return {"key": genome.key, "value": genome.value}

    def from_json(self, data: dict[str, Any]) -> TrivialGenome:
        key = int(data.get("key", 0))
        value = float(data.get("value", 0.5))
        return TrivialGenome(value=value, key=key)

    def serialize_output(
        self, output: RepresentationOutput, genome: Any = None
    ) -> dict[str, Any]:
        if output.output_type != "grid" or not hasattr(output.data, "shape"):
            return {"image": "", "grid": []}
        arr = np.asarray(output.data)
        b64 = _rgb_to_png_base64(arr)
        return {"image": "data:image/png;base64," + b64, "grid": []}

    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        if out.output_type != "grid" or not hasattr(out.data, "shape"):
            return None
        grid = np.asarray(out.data)
        if grid.ndim == 3:
            grid = grid[:, :, 0]
        return grid if grid.ndim >= 2 else None

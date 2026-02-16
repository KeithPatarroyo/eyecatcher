"""Grid-substrate representation base.

Shared serialize_output, build_save_assets, get_save_filenames, and
get_grid_for_symmetry for CA and NCA. Subclasses set grid_size and implement
create_random, mutate, crossover, express, to_json, from_json.
"""

import json
from collections.abc import Callable
from typing import Any

import numpy as np

from ._image_util import serialize_grid_image
from .base import RepresentationBase
from .mixins import GridAnalyzable, Saveable
from .protocol import RepresentationOutput


class GridRepresentationBase(Saveable, GridAnalyzable, RepresentationBase):
    """Base for grid-substrate representations (CA, NCA).

    Subclasses set self.grid_size and implement create_random, mutate, crossover,
    express, to_json, from_json. This base provides grid-specific serialize_output,
    build_save_assets, get_save_filenames, and get_grid_for_symmetry.
    """

    grid_size: int  # set by subclass __init__

    def serialize_output(
        self,
        output: RepresentationOutput,
        genome: Any = None,
    ) -> dict[str, Any]:
        """Serialize grid output for API; add genome-specific keys via hook."""
        result = serialize_grid_image(output)
        if genome is not None:
            result.update(self._serialize_genome_extras(genome))
        return result

    def _serialize_genome_extras(self, genome: Any) -> dict[str, Any]:
        """Hook for subclass-specific keys. CA adds genome grid, NCA adds rule+nodes."""
        return {}

    def build_save_assets(
        self,
        genome: Any,
        individual_id: int,
        **kwargs: Any,
    ) -> dict[str, bytes]:
        """Express to image, then PNG + genome JSON."""
        to_png_bytes: Callable[[np.ndarray], bytes] | None = kwargs.get("to_png_bytes")
        if not callable(to_png_bytes):
            return {}
        out = self.express(genome, {})
        if not hasattr(out.data, "shape"):
            return {}
        names = self.get_save_filenames(individual_id)
        arr = np.asarray(out.data)
        return {
            names["png"]: to_png_bytes(arr),
            names["genome_json"]: json.dumps(self.to_json(genome), indent=2).encode(
                "utf-8"
            ),
        }

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """Default filenames for grid save bundle."""
        return {
            "png": f"pattern_{individual_id}.png",
            "genome_json": f"genome_{individual_id}.json",
            "zip": f"pattern_{individual_id}.zip",
        }

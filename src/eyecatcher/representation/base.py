"""Representation base: required contract and optional defaults.

Subclass RepresentationBase to add a new representation; implement the
abstract methods and override only what differs from the defaults.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

import numpy as np

from .protocol import OutputType, Phenotype, RepresentationOutput


class RepresentationBase(ABC):
    """
    Abstract base for all representations. Defines the required contract
    (abstract methods) and default implementations for optional features.

    Subclasses must set: id, signal_spec, frontend_metadata.
    output_type is derived from phenotype.substrate. Capabilities are auto-derived.
    """

    @property
    def output_type(self) -> OutputType:
        """Derive from phenotype.substrate."""
        return cast(OutputType, self.phenotype.substrate)

    @property
    def phenotype(self) -> Phenotype:
        """Default: image substrate (static display from render_to_image)."""
        return Phenotype(substrate="image")

    @property
    def capabilities(self) -> dict[str, bool]:
        """Derive capability flags from which optional methods are overridden."""
        base = RepresentationBase
        cls = type(self)
        return {
            "save": cls.build_save_assets is not base.build_save_assets,
            "network": cls.get_network_data is not base.get_network_data,
            "time_output": cls.query_time_output is not base.query_time_output,
            "adjust_weight": cls.adjust_weight is not base.adjust_weight,
            "compile": cls.compile_to_shader is not base.compile_to_shader,
        }

    # --- Genome operations (required) ---

    @abstractmethod
    def create_random(self, key: int = 0) -> Any:
        """Create a new random individual."""
        ...

    @abstractmethod
    def mutate(self, ind: Any, key: int) -> Any:
        """Return a mutated copy of ind."""
        ...

    @abstractmethod
    def crossover(self, a: Any, b: Any, key: int) -> Any:
        """Return offspring from a and b."""
        ...

    # --- Development (genome → phenotype; required) ---
    @abstractmethod
    def express(
        self, ind: Any, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Produce displayable output."""
        ...

    # --- Serialization (required) ---
    @abstractmethod
    def to_json(self, ind: Any) -> dict[str, Any]:
        """Serialize individual for API/client."""
        ...

    @abstractmethod
    def from_json(self, data: dict[str, Any]) -> Any:
        """Deserialize individual from API/client payload."""
        ...

    # --- Phenotype sampling & optional (defaults; override to enable) ---

    def compile_to_shader(self, ind: Any, color_mode: str | None = None) -> str | None:
        """Return GLSL shader or None if unsupported."""
        return None

    def serialize_express_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """Serialize express output for API response. Override per output_type."""
        return {}

    def sample_rgb(
        self,
        ind: Any,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        """No RGB sampling (e.g. grid representations use express instead)."""
        return []

    def render_to_image(
        self,
        ind: Any,
        resolution: int | None = None,
        **kwargs: Any,
    ) -> np.ndarray | None:
        """Unsupported."""
        return None

    def get_individual_id(self, ind: Any) -> int:
        """Individuals expose a .key attribute."""
        return ind.key

    def get_network_types(self) -> tuple[str, ...]:
        """No adjust_weight networks."""
        return ()

    def has_temporal_signals(self) -> bool:
        """No temporal inputs."""
        return False

    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        """Not applicable (non-grid)."""
        return None

    def get_neat_pop_size(self) -> int | None:
        """Not NEAT."""
        return None

    def get_compile_stats(self, ind: Any) -> dict[str, Any]:
        """No network stats."""
        return {"nodes": 0, "connections": 0}

    def serialize_individual_extra(self, ind: Any) -> dict[str, Any]:
        """No extra keys per individual."""
        return {}

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """Default: png and zip only."""
        return {
            "png": f"pattern_{individual_id}.png",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: Any, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """Unsupported."""
        return {}

    def query_time_output(
        self, ind: Any, inputs: dict[str, float]
    ) -> dict[str, Any] | None:
        """Unsupported."""
        return None

    def get_network_data(self, ind: Any) -> dict[str, Any] | None:
        """Unsupported."""
        return None

    def adjust_weight(
        self,
        ind: Any,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        """Unsupported."""
        return None

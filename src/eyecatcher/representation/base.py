"""Representation base: optional defaults (mixin) and abstract contract (ABC).

OptionalRepresentationDefaults provides a single place for "unsupported" behavior
for optional protocol methods (no network, no time, no save, etc.). Subclass
RepresentationBase to add a new representation; implement the abstract methods
and override only what differs from these defaults.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from .protocol import RepresentationOutput


class OptionalRepresentationDefaults:
    """
    Mixin providing default implementations for optional representation methods
    when the representation does not support the feature (no network, no time,
    no RGB sampling, etc.). Keeps "unsupported" behavior in one named place
    instead of the abstract base.
    """

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


class RepresentationBase(OptionalRepresentationDefaults, ABC):
    """
    Abstract base for all representations. Defines only the required contract
    (abstract methods); optional behaviour comes from OptionalRepresentationDefaults.

    Subclasses must set: id, output_type, signal_spec, capabilities, frontend_metadata.
    """

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

    @abstractmethod
    def express(
        self, ind: Any, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Produce displayable output."""
        ...

    @abstractmethod
    def compile_to_shader(self, ind: Any, color_mode: str | None = None) -> str | None:
        """Return GLSL shader or None."""
        ...

    @abstractmethod
    def to_json(self, ind: Any) -> dict[str, Any]:
        """Serialize individual for API/client."""
        ...

    @abstractmethod
    def from_json(self, data: dict[str, Any]) -> Any:
        """Deserialize individual from API/client payload."""
        ...

    @abstractmethod
    def serialize_express_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """Serialize express output for API response."""
        ...

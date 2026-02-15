"""Capability mixins for representations.

Optional behaviors (save, network inspection, RGB sampling, grid analysis) are
expressed as mixins. API and fitness code check capabilities via
isinstance(rep, Saveable) etc., instead of introspecting method identity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from .protocol import RepresentationOutput


class Saveable(ABC):
    """Mixin: representation can produce save assets (PNG, GLSL, zip, etc.)."""

    @abstractmethod
    def build_save_assets(
        self, genome: Any, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """Build filename -> raw bytes for all assets to include in the save zip."""
        ...

    @abstractmethod
    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """Return logical filenames for saved assets (e.g. png, glsl, zip)."""
        ...


class NetworkInspectable(ABC):
    """Mixin: has network visualization and weight adjustment."""

    def get_network_types(self) -> tuple[str, ...]:
        """Return allowed network names for adjust_weight; empty if not supported."""
        return ()

    @abstractmethod
    def get_network_data(self, genome: Any) -> dict[str, Any] | None:
        """Return network visualization data for a genome, or None if unsupported."""
        ...

    @abstractmethod
    def adjust_weight(
        self,
        genome: Any,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        """Adjust a connection weight and return updated shader and genome, or None."""
        ...


class Samplable(ABC):
    """Mixin: can sample RGB at coordinates (for fitness)."""

    @abstractmethod
    def sample_rgb(
        self,
        genome: Any,
        coords: list[tuple[float, float]],
        time: float = 0.0,
    ) -> list[list[float]]:
        """Return [r,g,b] per coordinate for fitness/sampling."""
        ...


class GridAnalyzable(ABC):
    """Mixin: can provide a 2D grid for symmetry fitness."""

    @abstractmethod
    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        """Return a 2D grid for symmetry fitness, or None if not applicable."""
        ...

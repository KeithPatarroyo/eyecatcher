"""Representation protocol: common interface for evolvable representations.

CPPN, CA, etc. Evolution and API use this interface only. Capability
requirements per endpoint: see API_REQUIREMENTS.md.

Concrete implementations subclass RepresentationBase (base.py), which provides
optional defaults and auto-derived capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeVar, Union

import numpy as np

from ..signals.spec import SignalSpec

IndividualT = TypeVar("IndividualT")

OutputType = Literal["shader", "image", "grid", "audio"]

# Data for each output type: shader=str, image/grid/audio=ndarray
RepresentationOutputData = Union[str, np.ndarray]


@dataclass(frozen=True)
class Phenotype:
    """
    Declarative description of how this representation's phenotype is expressed
    and displayed. One per representation; exported to frontend via codegen.
    The substrate is the physical body (shader surface, grid, image) the phenotype
    is expressed on.
    """

    substrate: str  # "shader", "grid", "image", etc.
    # Grid-substrate fields (optional):
    grid_size: int | None = None
    step_interval_ms: int | None = None
    step_shader: str | None = None  # GLSL for the update rule (behavior)
    display_shader: str | None = None  # GLSL for visualization
    toggle_shader: str | None = None  # GLSL for toggle interaction (grid only)
    state_format: str | None = None  # "RGBA" or "RGBA16F"
    wrap: str | None = None  # "REPEAT" or "CLAMP"
    interactions: list[str] = field(default_factory=list)  # ["toggle", "draw"]
    # Metadata:
    meta_template: str | None = None  # e.g. "Nodes: {nodes} | Connections: ..."


class RepresentationOutput:
    """Tagged union for display payload; frontend uses output_type for renderer."""

    __slots__ = ("output_type", "data")

    def __init__(self, output_type: OutputType, data: RepresentationOutputData) -> None:
        self.output_type = output_type
        self.data = data


# Frontend metadata: hasSignalControls, genomeKeys, excludeKeys, capabilities.
RepresentationFrontendMetadata = dict[str, object]


class Representation(Protocol[IndividualT]):
    """
    Protocol for pluggable representations.

    All evolvable models (CPPN, NCA, CA, neural net) implement this interface.

    Optional class attribute: frontend_metadata (dict). When set, it is the single
    source for codegen (hasSignalControls, genomeKeys, capabilities, optional
    excludeKeys). See export.export_representations_for_frontend().

    output_type is derived from phenotype.substrate (shader, grid, image, etc.)
    unless a representation overrides it.
    """

    id: str

    # --- Phenotype (what is displayed) ---
    @property
    def output_type(self) -> OutputType:
        """Display/output type; default from phenotype.substrate."""
        ...

    signal_spec: SignalSpec

    @property
    def phenotype(self) -> Phenotype:
        """How this representation is expressed and displayed."""
        ...

    @property
    def capabilities(self) -> dict[str, bool]:
        """Capability flags (save, network, time_output, adjust_weight, compile)."""
        ...

    # --- Genome operations (evolution) ---
    def create_random(self, key: int = 0) -> IndividualT:
        """Create a new random individual. key is used as genome/id."""
        ...

    def mutate(self, ind: IndividualT, key: int) -> IndividualT:
        """Return a mutated copy of ind with the given key."""
        ...

    def crossover(self, a: IndividualT, b: IndividualT, key: int) -> IndividualT:
        """Return offspring from a and b with the given key."""
        ...

    # --- Development (genome → phenotype) ---
    def express(
        self, ind: IndividualT, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Produce displayable output (image, grid, etc.)."""
        ...

    def compile_to_shader(
        self, ind: IndividualT, color_mode: str | None = None
    ) -> str | None:
        """
        Return GLSL fragment shader for real-time display, or None to use
        CPU evaluate + texture upload. color_mode (e.g. 'hsv', 'rgb') is optional.
        """
        ...

    # --- Phenotype sampling (fitness, export) ---
    def sample_rgb(
        self, ind: IndividualT, coords: list[tuple[float, float]], time: float = 0.0
    ) -> list[list[float]]:
        """
        Optional: return [r,g,b] per coordinate for fitness/sampling.
        Default returns [] (e.g. CA uses express instead).
        """
        return []

    def render_to_image(
        self, ind: IndividualT, resolution: int | None = None, **kwargs: Any
    ) -> np.ndarray | None:
        """
        Optional: return RGB image array for save/export, or None if unsupported.
        """
        return None

    # --- Serialization (API, save/load) ---
    def to_json(self, ind: IndividualT) -> dict[str, Any]:
        """Serialize individual for API/client."""
        ...

    def from_json(self, data: dict[str, Any]) -> IndividualT:
        """Deserialize individual from API/client payload."""
        ...

    def get_individual_id(self, ind: IndividualT) -> int:
        """Return the individual's id (e.g. genome key) for API and evolution."""
        ...

    # --- Optional: introspection, save assets, API extensions ---
    def get_network_types(self) -> tuple[str, ...]:
        """Return allowed network names for adjust_weight; empty if not supported."""
        return ()

    def has_temporal_signals(self) -> bool:
        """True if the representation has temporal input signals (e.g. time)."""
        ...

    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        """
        Return a 2D grid for symmetry fitness, or None if not applicable.
        Used by ca_symmetry fitness; grid representations return out.data as 2D.
        """
        ...

    def get_neat_pop_size(self) -> int | None:
        """Return NEAT pop_size if this representation uses NEAT; None otherwise."""
        return None

    def get_compile_stats(self, ind: IndividualT) -> dict[str, Any]:
        """
        Return per-network node/connection stats for compile response.

        Representations with network visualization return a dict like
        { visual_nodes, visual_connections, time_nodes, time_connections };
        others return {"nodes": 0, "connections": 0}.
        """
        return {"nodes": 0, "connections": 0}

    def serialize_individual_extra(self, ind: IndividualT) -> dict[str, Any]:
        """
        Optional: extra key-value pairs to merge into response for this individual.

        E.g. CA: {"rule": int(ind.rule)}; CPPN: {}.
        """
        return {}

    def get_save_filenames(self, individual_id: int) -> dict[str, str]:
        """
        Return logical filenames for saved assets (e.g. png, glsl, zip).

        Keys match those returned by build_save_assets. Used for zip name and
        serve_saved_* routes.
        """
        return {
            "png": f"pattern_{individual_id}.png",
            "zip": f"pattern_{individual_id}.zip",
        }

    def build_save_assets(
        self, ind: IndividualT, individual_id: int, **kwargs: Any
    ) -> dict[str, bytes]:
        """
        Build filename -> raw bytes for all assets to include in the save zip.

        Representations override to add shader, genome JSON, network PDF, etc.
        Default returns empty dict (caller may treat as unsupported).
        """
        return {}

    def query_time_output(
        self, ind: IndividualT, inputs: dict[str, float]
    ) -> dict[str, Any] | None:
        """
        Optional: query time/signal output for debug panel.
        Returns {"timeOutput": float, "inputs": {...}} or None if unsupported.
        """
        return None

    def get_network_data(self, ind: IndividualT) -> dict[str, Any] | None:
        """
        Optional: return network visualization data for a genome.
        Returns {"nodes": [...], "connections": [...]} or None if unsupported.
        """
        return None

    def adjust_weight(
        self,
        ind: IndividualT,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        """
        Optional: adjust a connection weight and return updated shader and genome.
        Returns {"shader": str, "individual": dict} or None if unsupported.
        """
        return None

    def serialize_express_output(self, output: RepresentationOutput) -> dict[str, Any]:
        """
        Serialize express output for API response (e.g. /api/evaluate).
        Each representation returns the keys it needs
        (image, shader, grid, audio_data, etc.).
        """
        ...

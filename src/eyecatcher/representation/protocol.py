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

from ..signals.sensory_system import SensorySystem

GenomeT = TypeVar("GenomeT")

OutputType = Literal["field", "image", "grid", "audio"]

# Data for each output type: field=str (GLSL), image/grid/audio=ndarray
RepresentationOutputData = Union[str, np.ndarray]


@dataclass(frozen=True)
class Substrate:
    """The physical medium: where the organism exists.

    Types: "field" (continuous 2D morphogenetic field), "grid" (discrete lattice),
    "image" (static raster).
    """

    type: str  # "field", "grid", "image"
    grid_size: int | None = None
    state_format: str | None = None  # "RGBA", "RGBA16F"
    wrap: str | None = None  # "REPEAT", "CLAMP"


@dataclass(frozen=True)
class Behaviour:
    """Dynamics: how the organism changes over time and responds to interaction.

    Empty for static representations (e.g. CPPN fields).
    """

    update_rule: str | None = None  # GLSL for state transitions
    update_interval_ms: int | None = None
    interaction_rule: str | None = None  # GLSL for responding to stimuli
    interactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Phenotype:
    """Observable traits: what the organism looks like and how it exists."""

    substrate: Substrate
    display_rule: str | None = None  # GLSL for visualization
    meta_template: str | None = None
    behaviour: Behaviour = field(default_factory=Behaviour)


class RepresentationOutput:
    """Tagged union for display payload; frontend uses output_type for renderer."""

    __slots__ = ("output_type", "data")

    def __init__(self, output_type: OutputType, data: RepresentationOutputData) -> None:
        self.output_type = output_type
        self.data = data


# Frontend metadata: hasSignalControls, genomeKeys, excludeKeys, capabilities.
RepresentationFrontendMetadata = dict[str, object]


class Representation(Protocol[GenomeT]):
    """
    Protocol for pluggable representations.

    All evolvable models (CPPN, NCA, CA, neural net) implement this interface.

    Optional class attribute: frontend_metadata (dict). When set, it is the single
    source for codegen (hasSignalControls, genomeKeys, capabilities, optional
    excludeKeys). See export.export_representations_for_frontend().

    output_type is derived from phenotype.substrate.type (field, grid, image, etc.)
    unless a representation overrides it.
    """

    id: str

    # --- Phenotype (what is displayed) ---
    @property
    def output_type(self) -> OutputType:
        """Display/output type; default from phenotype.substrate."""
        ...

    sensory_system: SensorySystem

    @property
    def phenotype(self) -> Phenotype:
        """How this representation is expressed and displayed."""
        ...

    @property
    def capabilities(self) -> dict[str, bool]:
        """Capability flags (save, network, time_output, adjust_weight, develop)."""
        ...

    # --- Genome operations (evolution) ---
    def create_random(self, key: int = 0) -> GenomeT:
        """Create a new random genome. key is used as genome id."""
        ...

    def mutate(self, genome: GenomeT, key: int) -> GenomeT:
        """Return a mutated copy of genome with the given key."""
        ...

    def crossover(self, a: GenomeT, b: GenomeT, key: int) -> GenomeT:
        """Return offspring from a and b with the given key."""
        ...

    # --- Development (genome → phenotype) ---
    def express(
        self, genome: GenomeT, inputs: dict[str, float], **kwargs: Any
    ) -> RepresentationOutput:
        """Produce displayable output (image, grid, etc.)."""
        ...

    def develop(self, genome: GenomeT, color_mode: str | None = None) -> str | None:
        """
        Return GLSL rendering rule for real-time display, or None to use
        CPU express + texture upload. color_mode (e.g. 'hsv', 'rgb') is optional.
        """
        ...

    # --- Serialization (API, save/load) ---
    def to_json(self, genome: GenomeT) -> dict[str, Any]:
        """Serialize genome for API/client."""
        ...

    def from_json(self, data: dict[str, Any]) -> GenomeT:
        """Deserialize genome from API/client payload."""
        ...

    def get_id(self, genome: GenomeT) -> int:
        """Return the genome's id (key) for API and evolution."""
        ...

    def serialize_output(
        self, output: RepresentationOutput, genome: GenomeT | None = None
    ) -> dict[str, Any]:
        """
        Serialize express output for API response (e.g. /api/express).
        Optionally include genome-based keys when genome is provided.
        Returns keys such as image, rule, grid, audio_data, etc.
        """
        ...

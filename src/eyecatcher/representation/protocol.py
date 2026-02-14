"""Representation protocol: common interface for evolvable representations.

CPPN, CA, etc. Evolution and API use this interface only. Capability
requirements per endpoint: see API_REQUIREMENTS.md.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypeVar, Union

import numpy as np

from ..signals.spec import SignalSpec

IndividualT = TypeVar("IndividualT")

OutputType = Literal["shader", "image", "grid", "audio"]

# Data for each output type: shader=str, image/grid/audio=ndarray
RepresentationOutputData = Union[str, np.ndarray]


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
    """

    id: str
    output_type: OutputType
    signal_spec: SignalSpec

    def create_random(self, key: int = 0) -> IndividualT:
        """Create a new random individual. key is used as genome/id."""
        ...

    def mutate(self, ind: IndividualT, key: int) -> IndividualT:
        """Return a mutated copy of ind with the given key."""
        ...

    def crossover(self, a: IndividualT, b: IndividualT, key: int) -> IndividualT:
        """Return offspring from a and b with the given key."""
        ...

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

    def to_json(self, ind: IndividualT) -> dict[str, Any]:
        """Serialize individual for API/client."""
        ...

    def from_json(self, data: dict[str, Any]) -> IndividualT:
        """Deserialize individual from API/client payload."""
        ...

    def get_compile_stats(self, ind: IndividualT) -> dict[str, Any] | None:
        """
        Return per-network node/connection stats for compile response, or None.

        Representations with network visualization (e.g. dual_cppn) return a dict
        like { visual_nodes, visual_connections, time_nodes, time_connections }.
        """
        return None

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

    def serialize_express_output(
        self, output: RepresentationOutput
    ) -> dict[str, Any] | None:
        """
        Optional: serialize express output for API response (e.g. /api/evaluate).
        Return None to use default serialization (grid->image, shader->shader).
        Non-visual representations (e.g. audio) implement this to add their payload.
        """
        return None


_CAPABILITIES_CACHE: dict[str, dict[str, bool]] = {}


def get_representation_capabilities(representation: Any) -> dict[str, bool]:
    """
    Derive capability flags from optional protocol methods.

    Uses declarative hints from signal_spec when present (e.g. socket "time"
    implies time_output; socket "visual" implies network). Otherwise creates a
    random individual once (cached by representation.id) and checks which
    optional methods return non-None / non-empty.
    """
    rid = getattr(representation, "id", None)
    if rid and rid in _CAPABILITIES_CACHE:
        return _CAPABILITIES_CACHE[rid].copy()

    declarative_time = False
    declarative_network = False
    spec = getattr(representation, "signal_spec", None)
    if spec is not None:
        try:
            spec.socket("time")
            declarative_time = True
        except KeyError:
            pass
        try:
            spec.socket("visual")
            declarative_network = True
        except KeyError:
            pass

    ind = representation.create_random(0)
    save = bool(representation.build_save_assets(ind, 0, to_png_bytes=lambda a: b""))
    get_network = getattr(representation, "get_network_data", None)
    network_data = get_network(ind) if callable(get_network) else None
    network = declarative_network or (network_data is not None)
    query_time = getattr(representation, "query_time_output", None)
    time_output = declarative_time or (
        query_time(ind, {}) is not None if callable(query_time) else False
    )
    adjust_weight = False
    if network_data and network_data.get("connections"):
        adj_meth = getattr(representation, "adjust_weight", None)
        if callable(adj_meth):
            conn = network_data["connections"][0]
            adj = adj_meth(
                ind,
                conn.get("network", "visual"),
                str(conn.get("source", "")),
                str(conn.get("target", "")),
                0.5,
            )
            adjust_weight = adj is not None

    caps = {
        "save": save,
        "network": network,
        "time_output": time_output,
        "adjust_weight": adjust_weight,
    }
    if rid:
        _CAPABILITIES_CACHE[rid] = caps.copy()
    return caps

"""
Substrate protocol: common interface for evolvable substrates.

CPPNs (dual, single), NCAs, CAs, and generic neural nets implement this
protocol so evolution and API stay substrate-agnostic.

Which API endpoints require which substrate capabilities is documented in
API_REQUIREMENTS.md (e.g. /api/compile requires compile_to_shader;
save/time-output/network require capabilities such as network, time_output).
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypeVar, Union

import numpy as np

IndividualT = TypeVar("IndividualT")

OutputType = Literal["shader", "image", "grid", "audio"]

# Data for each output type: shader=str, image/grid/audio=ndarray
SubstrateOutputData = Union[str, np.ndarray]


class SubstrateOutput:
    """Tagged union for display payload; frontend uses output_type for renderer."""

    __slots__ = ("output_type", "data")

    def __init__(self, output_type: OutputType, data: SubstrateOutputData) -> None:
        self.output_type = output_type
        self.data = data


class Substrate(Protocol[IndividualT]):
    """
    Protocol for pluggable substrates.

    All evolvable models (CPPN, NCA, CA, neural net) implement this interface.
    """

    id: str
    output_type: OutputType

    def create_random(self, key: int = 0) -> IndividualT:
        """Create a new random individual. key is used as genome/id."""
        ...

    def mutate(self, ind: IndividualT, key: int) -> IndividualT:
        """Return a mutated copy of ind with the given key."""
        ...

    def crossover(self, a: IndividualT, b: IndividualT, key: int) -> IndividualT:
        """Return offspring from a and b with the given key."""
        ...

    def evaluate(
        self, ind: IndividualT, inputs: dict[str, float], **kwargs: Any
    ) -> SubstrateOutput:
        """Produce displayable output (image, grid, etc.)."""
        ...

    def compile_to_shader(self, ind: IndividualT) -> str | None:
        """
        Return GLSL fragment shader for real-time display, or None to use
        CPU evaluate + texture upload.
        """
        ...

    def to_json(self, ind: IndividualT) -> dict[str, Any]:
        """Serialize individual for API/client."""
        ...

    def from_json(self, data: dict[str, Any]) -> IndividualT:
        """Deserialize individual from API/client payload."""
        ...

    def get_compile_stats(self, ind: IndividualT) -> dict[str, Any] | None:
        """
        Return per-network node/connection stats for compile response, or None.

        Substrates with network visualization (e.g. dual_cppn) return a dict
        like { visual_nodes, visual_connections, time_nodes, time_connections }.
        """
        return None

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

        Substrates override to add shader, genome JSON, network PDF, etc.
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
        Returns {"shader": str, "genome": dict} or None if unsupported.
        """
        return None


def get_substrate_capabilities(substrate: Any) -> dict[str, bool]:
    """
    Return capability flags for a substrate.
    Substrates may implement get_capabilities(); else returns defaults.
    """
    meth = getattr(substrate, "get_capabilities", None)
    if callable(meth):
        return meth()
    return {
        "save": True,
        "network": False,
        "time_output": False,
        "adjust_weight": False,
    }

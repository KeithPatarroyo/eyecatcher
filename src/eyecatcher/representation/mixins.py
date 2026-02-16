"""Capability mixins for representations.

Optional behaviors (save, network inspection, RGB sampling, grid analysis) are
expressed as mixins. API and fitness code check capabilities via
isinstance(rep, Saveable) etc., instead of introspecting method identity.
"""

from abc import ABC, abstractmethod
from typing import Any

import neat
import numpy as np

from .protocol import RepresentationOutput


class NeatEvolvable(ABC):
    """Mixin: default NEAT genome lifecycle.

    Requires: property neat_config returning neat.Config.
    Provides: create_random, mutate, crossover, to_json, from_json, get_neat_pop_size.
    DualCPPN overrides all genome ops (DualGenome wraps two NEAT genomes).
    """

    @property
    @abstractmethod
    def neat_config(self) -> neat.Config:
        """NEAT config for the primary genome."""
        ...

    def create_random(self, key: int = 0) -> neat.DefaultGenome:
        from ..genome.operators import create_random_genome

        return create_random_genome(self.neat_config, genome_id=key, key=key)

    def mutate(self, genome: neat.DefaultGenome, key: int) -> neat.DefaultGenome:
        from ..genome.operators import mutate_genome

        return mutate_genome(genome, self.neat_config, key=key)

    def crossover(
        self,
        a: neat.DefaultGenome,
        b: neat.DefaultGenome,
        key: int,
    ) -> neat.DefaultGenome:
        from ..genome.operators import crossover_genomes

        return crossover_genomes(a, b, self.neat_config, key=key)

    def to_json(self, genome: neat.DefaultGenome) -> dict[str, Any]:
        from ..genome.serialization import genome_to_json

        return genome_to_json(genome)

    def from_json(self, data: dict[str, Any]) -> neat.DefaultGenome:
        from ..genome.serialization import genome_from_json

        return genome_from_json(data, self.neat_config)

    def get_neat_pop_size(self) -> int | None:
        return getattr(self.neat_config, "pop_size", None)


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
    """Mixin: has network visualization and weight adjustment.

    Requires: property receptors -> tuple[NeatReceptor, ...].
    Optionally override _genome_for_receptor for compound genomes (e.g. DualCPPN).
    """

    @property
    @abstractmethod
    def receptors(self) -> tuple[Any, ...]:
        """NEAT receptors for network inspection; subclasses declare their list."""
        ...

    def _genome_for_receptor(self, genome: Any, receptor: Any) -> Any:
        """Return the sub-genome for this receptor. Default: genome itself."""
        return genome

    def get_network_types(self) -> tuple[str, ...]:
        """Return allowed network names for adjust_weight."""
        from .receptors import NeatReceptor

        return tuple(r.name for r in self.receptors if isinstance(r, NeatReceptor))

    def get_network_data(self, genome: Any) -> dict[str, Any] | None:
        """Return network visualization data for a genome."""
        from .receptors import NeatReceptor

        all_nodes: list[dict[str, Any]] = []
        all_connections: list[dict[str, Any]] = []
        for i, r in enumerate(self.receptors):
            if not isinstance(r, NeatReceptor):
                continue
            g = self._genome_for_receptor(genome, r)
            nodes, conns = r.extract_network_data(g, x_offset=i * 1000)
            all_nodes.extend(nodes)
            all_connections.extend(conns)
        return {"nodes": all_nodes, "connections": all_connections}

    def adjust_weight(
        self,
        genome: Any,
        network: str,
        source: str,
        target: str,
        weight: float,
    ) -> dict[str, Any] | None:
        """Adjust a connection weight and return updated rule and genome, or None."""
        from ..inspection import parse_network_node_id
        from .receptors import NeatReceptor

        receptor = next(
            (
                r
                for r in self.receptors
                if isinstance(r, NeatReceptor) and r.name == network
            ),
            None,
        )
        if not receptor:
            return None
        g = self._genome_for_receptor(genome, receptor)
        try:
            source_id = parse_network_node_id(source)
            target_id = parse_network_node_id(target)
        except (ValueError, TypeError):
            return None
        conn_key = (source_id, target_id)
        if conn_key not in g.connections:
            return None
        g.connections[conn_key].weight = weight
        return {"rule": self.develop(genome) or "", "individual": self.to_json(genome)}

    def get_develop_stats(self, genome: Any) -> dict[str, Any]:
        """Return per-network node/connection stats for develop response."""
        from .receptors import NeatReceptor

        stats: dict[str, Any] = {}
        for r in self.receptors:
            if isinstance(r, NeatReceptor):
                g = self._genome_for_receptor(genome, r)
                stats.update(r.network_stats(g))
        return stats if stats else {"nodes": 0, "connections": 0}


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

    def get_grid_for_symmetry(self, out: RepresentationOutput) -> np.ndarray | None:
        """Return a 2D grid for symmetry fitness, or None if not applicable."""
        if out.output_type != "grid" or not hasattr(out.data, "shape"):
            return None
        grid = np.asarray(out.data)
        if grid.ndim == 3:
            grid = grid[:, :, 0]
        return grid if grid.ndim >= 2 else None

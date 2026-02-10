"""
CPPN engine: main entry point that wires config, query, rendering, and operators.
"""

import logging
import os
import pickle
from typing import Optional

import neat

from .. import get_root_dir
from . import config as evolution_config
from .activation import register_custom_activations
from .genome import DualGenome
from .operators import (
    crossover_dual_genomes,
    crossover_single_genomes,
    mutate_dual_genome,
    mutate_single_genome,
)
from .query import query_cppn, query_dual_cppn, query_time_signal
from .rendering import (
    render_animation_frames as _render_animation_frames,
)
from .rendering import (
    render_dual_animation_frames as _render_dual_animation_frames,
)
from .rendering import (
    render_dual_image as _render_dual_image,
)
from .rendering import (
    render_image as _render_image,
)

logger = logging.getLogger(__name__)


class CPPNEngine:
    """
    Compositional Pattern Producing Network engine.
    Generates time-varying visual patterns using evolved neural networks.
    Supports dual-CPPN mode: visual network + time signal network per individual.
    """

    def __init__(
        self,
        config_path: str = evolution_config.NEAT_CONFIG_PATH,
        time_config_path: str = evolution_config.NEAT_TIME_CONFIG_PATH,
    ):
        """Initialize CPPN engine with NEAT configurations."""
        root = get_root_dir()
        if not os.path.isabs(config_path):
            config_path = os.path.join(root, config_path)
        if not os.path.isabs(time_config_path):
            time_config_path = os.path.join(root, time_config_path)

        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            config_path,
        )
        register_custom_activations(self.config)

        self.time_config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            time_config_path,
        )
        register_custom_activations(self.time_config)

        self.population = None
        self.time_population = None
        self.generation = 0

    def create_population(self) -> neat.Population:
        """Create initial populations for both visual and time signal CPPNs."""
        self.population = neat.Population(self.config)
        self.population.add_reporter(neat.StdOutReporter(False))
        stats = neat.StatisticsReporter()
        self.population.add_reporter(stats)
        self.time_population = neat.Population(self.time_config)
        return self.population

    def query_time_signal(
        self,
        time_genome: neat.DefaultGenome,
        raw_time: float,
        mouse_speed: float,
        mouse_distance: float = 0.0,
        inactivity: float = 0.0,
    ) -> float:
        """Query time signal CPPN for modified time. Returns value in -1 to 1."""
        return query_time_signal(
            time_genome,
            self.time_config,
            raw_time,
            mouse_speed,
            mouse_distance,
            inactivity,
        )

    def query_cppn(
        self,
        genome: neat.DefaultGenome,
        x: float,
        y: float,
        time: float = 0.0,
        mouse_speed: float = 0.0,
        mouse_distance: float = 0.0,
        inactivity: float = 0.0,
        distance: Optional[float] = None,
    ) -> tuple[float, float, float]:
        """Query visual CPPN for RGB at (x, y, time). Returns (r, g, b) in 0–1."""
        return query_cppn(
            genome,
            self.config,
            x,
            y,
            time,
            mouse_speed,
            mouse_distance,
            inactivity,
            distance,
        )

    def query_dual_cppn(
        self,
        dual_genome: DualGenome,
        x: float,
        y: float,
        raw_time: float = 0.0,
        mouse_speed: float = 0.0,
        mouse_distance: float = 0.0,
        inactivity: float = 0.0,
        distance: Optional[float] = None,
    ) -> tuple[float, float, float]:
        """Query dual CPPN for RGB at (x,y,raw_time). Returns (r,g,b) in 0–1."""
        return query_dual_cppn(
            dual_genome,
            self.config,
            self.time_config,
            x,
            y,
            raw_time,
            mouse_speed,
            mouse_distance,
            inactivity,
            distance,
        )

    def render_image(
        self,
        genome: neat.DefaultGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        time: float = 0.0,
    ):
        """Render a full image from a CPPN at a given time."""
        return _render_image(genome, self.config, resolution, time)

    def render_animation_frames(
        self,
        genome: neat.DefaultGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        num_frames: int = evolution_config.DEFAULT_NUM_FRAMES,
        time_range: tuple[float, float] = (0.0, 1.0),
    ):
        """Render multiple frames for animation."""
        return _render_animation_frames(
            genome, self.config, resolution, num_frames, time_range
        )

    def render_dual_image(
        self,
        dual_genome: DualGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        raw_time: float = 0.5,
        mouse_speed: float = 0.0,
        mouse_distance: float = 0.0,
        inactivity: float = 0.0,
    ):
        """Render a complete image from a dual CPPN at a given raw time."""
        return _render_dual_image(
            dual_genome,
            self.config,
            self.time_config,
            resolution,
            raw_time,
            mouse_speed,
            mouse_distance,
            inactivity,
        )

    def render_dual_animation_frames(
        self,
        dual_genome: DualGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        num_frames: int = evolution_config.DEFAULT_NUM_FRAMES,
        time_range: tuple[float, float] = (0.0, 1.0),
        mouse_speed: float = 0.0,
        mouse_distance: float = 0.0,
        inactivity: float = 0.0,
    ):
        """Render multiple frames for a dual CPPN animation."""
        return _render_dual_animation_frames(
            dual_genome,
            self.config,
            self.time_config,
            resolution,
            num_frames,
            time_range,
            mouse_speed,
            mouse_distance,
            inactivity,
        )

    def save_genome(
        self, genome: neat.DefaultGenome, filepath: str, visualize: bool = False
    ):
        """Save a genome to file. If visualize=True, also create network PDF."""
        with open(filepath, "wb") as f:
            pickle.dump(genome, f)
        if visualize:
            from .genome_visualizer import render_genome_network_pdf

            viz_path = filepath.replace(".pkl", "_network.pdf")
            render_genome_network_pdf(genome, self.config, viz_path)

    def load_genome(self, filepath: str) -> neat.DefaultGenome:
        """Load a genome from file."""
        with open(filepath, "rb") as f:
            return pickle.load(f)

    def mutate_genome(self, genome: neat.DefaultGenome) -> neat.DefaultGenome:
        """Create a mutated copy of a visual genome (legacy support)."""
        return mutate_single_genome(genome, self.config)

    def mutate_dual_genome(self, dual_genome: DualGenome, new_key: int) -> DualGenome:
        """Create a mutated copy of a dual genome."""
        return mutate_dual_genome(dual_genome, self.config, self.time_config, new_key)

    def crossover_genomes(
        self, genome1: neat.DefaultGenome, genome2: neat.DefaultGenome
    ) -> neat.DefaultGenome:
        """Create offspring from two visual genomes (legacy support)."""
        return crossover_single_genomes(genome1, genome2, self.config)

    def crossover_dual_genomes(
        self, dual1: DualGenome, dual2: DualGenome, new_key: int
    ) -> DualGenome:
        """Create offspring from two dual genomes."""
        return crossover_dual_genomes(
            dual1, dual2, self.config, self.time_config, new_key
        )

    def save_dual_genome(
        self, dual_genome: DualGenome, filepath: str, visualize: bool = False
    ):
        """Save a dual genome to file. If visualize=True, also create network PDF."""
        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "visual": dual_genome.visual,
                    "time_signal": dual_genome.time_signal,
                    "key": dual_genome.key,
                },
                f,
            )
        if visualize:
            from .genome_visualizer import render_genome_network_pdf

            viz_path = filepath.replace(".pkl", "_network.pdf")
            render_genome_network_pdf(dual_genome.visual, self.config, viz_path)

    def load_dual_genome(self, filepath: str) -> DualGenome:
        """Load a dual genome from file."""
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            return DualGenome(
                visual=data["visual"],
                time_signal=data["time_signal"],
                key=data.get("key", 0),
            )

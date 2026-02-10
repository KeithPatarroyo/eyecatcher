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
from .operators import crossover_dual_genomes, mutate_dual_genome
from .query import query_dual_cppn, query_time_signal, query_visual_cppn
from .rendering import (
    render_dual_animation_frames as _render_dual_animation_frames,
)
from .rendering import render_dual_image as _render_dual_image
from .signals import (
    TIME_INPUTS,
    TIME_OUTPUTS,
    VISUAL_INPUTS,
    VISUAL_OUTPUTS,
)

logger = logging.getLogger(__name__)


def _validate_neat_config(config, signals, outputs, config_name: str) -> None:
    """Assert NEAT config num_inputs/num_outputs match the signal registry."""
    actual_in = config.genome_config.num_inputs
    expected_in = len(signals)
    assert (
        actual_in == expected_in
    ), f"{config_name}: num_inputs={actual_in}, registry has {expected_in}"
    actual_out = config.genome_config.num_outputs
    expected_out = len(outputs)
    assert (
        actual_out == expected_out
    ), f"{config_name}: num_outputs={actual_out}, registry has {expected_out}"


class CPPNEngine:
    """
    Config holder and facade for dual-CPPN operations.

    Holds NEAT configs (visual and time) and delegates to evolution module
    functions (query, rendering, operators). Use this as the single entry
    point from server/stateless API; keep logic in the modules.
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

        _validate_neat_config(self.config, VISUAL_INPUTS, VISUAL_OUTPUTS, "visual")
        _validate_neat_config(self.time_config, TIME_INPUTS, TIME_OUTPUTS, "time")

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
        inputs: dict[str, float],
    ) -> float:
        """Query time signal CPPN for modified time. Returns value in -1 to 1.

        inputs: dict of signal name -> value (raw_time, mouse_speed, ...).
        """
        return query_time_signal(time_genome, self.time_config, inputs)

    def query_visual_cppn(
        self,
        genome: neat.DefaultGenome,
        inputs: dict[str, float],
    ) -> tuple[float, float, float]:
        """Query visual CPPN for RGB. Returns (r, g, b) in 0–1.

        inputs: dict of signal name -> value (x, y, time, ...).
        """
        return query_visual_cppn(genome, self.config, inputs)

    def query_dual_cppn(
        self,
        dual_genome: DualGenome,
        inputs: dict[str, float],
    ) -> tuple[float, float, float]:
        """Query dual CPPN for RGB. Returns (r,g,b) in 0–1.

        inputs: dict with x, y and time-CPPN inputs (raw_time, ...).
        """
        return query_dual_cppn(
            dual_genome,
            self.config,
            self.time_config,
            inputs,
        )

    def render_dual_image(
        self,
        dual_genome: DualGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        extra_inputs: Optional[dict] = None,
    ):
        """Render a complete image from a dual CPPN.

        extra_inputs: dict of signal name -> value (from evolution.signals registry).
        """
        return _render_dual_image(
            dual_genome,
            self.config,
            self.time_config,
            resolution,
            extra_inputs,
        )

    def render_dual_animation_frames(
        self,
        dual_genome: DualGenome,
        resolution: int = evolution_config.PREVIEW_RENDER_RESOLUTION,
        num_frames: int = evolution_config.DEFAULT_NUM_FRAMES,
        time_range: tuple[float, float] = (0.0, 1.0),
        extra_inputs: Optional[dict] = None,
    ):
        """Render multiple frames for a dual CPPN animation.

        extra_inputs: optional base signal values (from registry).
        """
        return _render_dual_animation_frames(
            dual_genome,
            self.config,
            self.time_config,
            resolution,
            num_frames,
            time_range,
            extra_inputs,
        )

    def mutate_dual_genome(self, dual_genome: DualGenome, new_key: int) -> DualGenome:
        """Create a mutated copy of a dual genome."""
        return mutate_dual_genome(dual_genome, self.config, self.time_config, new_key)

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

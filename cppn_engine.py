"""
CPPN Engine for generating time-varying patterns.
Uses NEAT-Python for evolution.

Supports dual-CPPN individuals where each individual has:
- A visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- A time signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)
"""
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional

import neat
import numpy as np
import pickle


def _cos_activation(x):
    """Cosine activation function."""
    return math.cos(x)


@dataclass
class DualGenome:
    """
    A paired genome consisting of a visual CPPN and a time signal CPPN.
    Both are evolved together with shared fitness.
    """
    visual: neat.DefaultGenome
    time_signal: neat.DefaultGenome
    key: int = 0
    
    @property
    def fitness(self):
        """Return fitness (stored on visual genome)."""
        return self.visual.fitness
    
    @fitness.setter
    def fitness(self, value):
        """Set fitness on both genomes."""
        self.visual.fitness = value
        self.time_signal.fitness = value


class CPPNEngine:
    """
    Compositional Pattern Producing Network engine.
    Generates time-varying visual patterns using evolved neural networks.
    
    Supports dual-CPPN mode where each individual has both a visual network
    and a time signal network that shapes how time flows.
    """
    
    def __init__(self, 
                 config_path: str = "config/neat_config.txt",
                 time_config_path: str = "config/neat_config_time.txt"):
        """Initialize CPPN engine with NEAT configurations."""
        # Visual CPPN config
        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            config_path
        )
        self._register_custom_activations(self.config)
        
        # Time signal CPPN config
        self.time_config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            time_config_path
        )
        self._register_custom_activations(self.time_config)
        
        self.population = None
        self.time_population = None
        self.generation = 0
    
    def _register_custom_activations(self, config: neat.Config):
        """Register custom activation functions with a config."""
        activation_defs = config.genome_config.activation_defs
        
        # Register 'cos' if not already present
        if 'cos' not in activation_defs.functions:
            activation_defs.add('cos', _cos_activation)
        
    def create_population(self) -> neat.Population:
        """Create initial populations for both visual and time signal CPPNs."""
        # Visual CPPN population
        self.population = neat.Population(self.config)
        self.population.add_reporter(neat.StdOutReporter(False))  # Quiet mode
        stats = neat.StatisticsReporter()
        self.population.add_reporter(stats)
        
        # Time signal CPPN population (needed to initialize innovation tracker)
        self.time_population = neat.Population(self.time_config)
        
        return self.population
    
    def query_time_signal(self,
                          time_genome: neat.DefaultGenome,
                          raw_time: float,
                          mouse_speed: float,
                          mouse_distance: float = 0.0,
                          inactivity: float = 0.0) -> float:
        """
        Query the time signal CPPN to get a modified time value.
        
        Args:
            time_genome: Time signal NEAT genome
            raw_time: Raw time value (normalized -1 to 1)
            mouse_speed: Mouse movement speed (normalized -1 to 1)
            mouse_distance: Distance from mouse to pattern center (normalized -1 to 1)
            inactivity: Activity level - boosted by speed, decays when still (normalized -1 to 1)
            
        Returns:
            Modified time value (normalized -1 to 1)
        """
        # Time signal inputs: raw_time, mouse_speed, mouse_distance, inactivity, bias
        inputs = [raw_time, mouse_speed, mouse_distance, inactivity, 1.0]
        
        # Create network and activate
        net = neat.nn.FeedForwardNetwork.create(time_genome, self.time_config)
        outputs = net.activate(inputs)
        
        # Clamp output to -1 to 1 range (keep as time signal, not 0-1)
        return max(-1.0, min(1.0, outputs[0]))
    
    def query_cppn(self, 
                   genome: neat.DefaultGenome, 
                   x: float, 
                   y: float, 
                   time: float = 0.0,
                   mouse_speed: float = 0.0,
                   mouse_distance: float = 0.0,
                   inactivity: float = 0.0,
                   distance: Optional[float] = None) -> Tuple[float, float, float]:
        """
        Query a visual CPPN for RGB values at given coordinates and time.
        
        Args:
            genome: NEAT genome to evaluate (visual CPPN)
            x: X coordinate (normalized -1 to 1)
            y: Y coordinate (normalized -1 to 1)
            time: Time value (normalized -1 to 1)
            mouse_speed: Mouse movement speed (normalized -1 to 1)
            mouse_distance: Distance from mouse to pattern center (normalized -1 to 1)
            inactivity: Activity level - boosted by speed, decays when still (normalized -1 to 1)
            distance: Distance from center (computed if None)
            
        Returns:
            RGB values (each 0-1)
        """
        if distance is None:
            distance = np.sqrt(x**2 + y**2)
        
        # CPPN inputs: x, y, distance, time, mouse_speed, mouse_distance, inactivity, bias
        inputs = [x, y, distance, time, mouse_speed, mouse_distance, inactivity, 1.0]
        
        # Create network and activate
        net = neat.nn.FeedForwardNetwork.create(genome, self.config)
        outputs = net.activate(inputs)
        
        # Clamp outputs to 0-1 range
        r = max(0.0, min(1.0, (outputs[0] + 1.0) / 2.0))
        g = max(0.0, min(1.0, (outputs[1] + 1.0) / 2.0))
        b = max(0.0, min(1.0, (outputs[2] + 1.0) / 2.0))
        
        return r, g, b
    
    def query_dual_cppn(self,
                        dual_genome: DualGenome,
                        x: float,
                        y: float,
                        raw_time: float = 0.0,
                        mouse_speed: float = 0.0,
                        mouse_distance: float = 0.0,
                        inactivity: float = 0.0,
                        distance: Optional[float] = None) -> Tuple[float, float, float]:
        """
        Query a dual CPPN (time signal + visual) for RGB values.
        
        The time signal CPPN first transforms the raw time based on mouse speed,
        distance and activity, then the visual CPPN uses this modified time.
        
        Args:
            dual_genome: DualGenome containing visual and time_signal genomes
            x: X coordinate (normalized -1 to 1)
            y: Y coordinate (normalized -1 to 1)
            raw_time: Raw time value (normalized -1 to 1)
            mouse_speed: Mouse movement speed (normalized -1 to 1)
            mouse_distance: Distance from mouse to pattern center (normalized -1 to 1)
            inactivity: Activity level - boosted by speed, decays when still (normalized -1 to 1)
            distance: Distance from center (computed if None)
            
        Returns:
            RGB values (each 0-1)
        """
        # First, get the modified time from the time signal CPPN
        modified_time = self.query_time_signal(
            dual_genome.time_signal, raw_time, mouse_speed, mouse_distance, inactivity
        )
        
        # Then query the visual CPPN with the modified time
        return self.query_cppn(
            dual_genome.visual, x, y, modified_time, mouse_speed, mouse_distance, inactivity, distance
        )
    
    def render_image(self, 
                    genome: neat.DefaultGenome, 
                    resolution: int = 256,
                    time: float = 0.0) -> np.ndarray:
        """
        Render a complete image from a CPPN at a specific time.
        
        Args:
            genome: NEAT genome to render
            resolution: Image size (will be resolution x resolution)
            time: Time value for animation (0-1)
            
        Returns:
            RGB image as numpy array (resolution x resolution x 3)
        """
        img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
        
        for i in range(resolution):
            for j in range(resolution):
                # Normalize coordinates to -1 to 1
                x = -1.0 + (i / resolution) * 2.0
                y = -1.0 + (j / resolution) * 2.0
                
                # Normalize time to -1 to 1
                t = -1.0 + time * 2.0
                
                r, g, b = self.query_cppn(genome, x, y, t)
                
                img[j, i] = [int(r * 255), int(g * 255), int(b * 255)]
        
        return img
    
    def render_animation_frames(self,
                               genome: neat.DefaultGenome,
                               resolution: int = 256,
                               num_frames: int = 30,
                               time_range: Tuple[float, float] = (0.0, 1.0)) -> list:
        """
        Render multiple frames for animation.
        
        Args:
            genome: NEAT genome to render
            resolution: Image size
            num_frames: Number of frames to generate
            time_range: (start_time, end_time) for animation
            
        Returns:
            List of numpy arrays (images)
        """
        frames = []
        start_time, end_time = time_range
        
        for frame_idx in range(num_frames):
            t = start_time + (end_time - start_time) * (frame_idx / num_frames)
            frame = self.render_image(genome, resolution, t)
            frames.append(frame)
            
        return frames
    
    def render_dual_image(self,
                          dual_genome: DualGenome,
                          resolution: int = 256,
                          raw_time: float = 0.5,
                          mouse_speed: float = 0.0,
                          mouse_distance: float = 0.0,
                          inactivity: float = 0.0) -> np.ndarray:
        """
        Render a complete image from a dual CPPN at a given raw time.
        Uses query_dual_cppn so the time-signal CPPN shapes the visual output.
        """
        img = np.zeros((resolution, resolution, 3), dtype=np.uint8)
        for i in range(resolution):
            for j in range(resolution):
                x = -1.0 + (i / resolution) * 2.0
                y = -1.0 + (j / resolution) * 2.0
                r, g, b = self.query_dual_cppn(
                    dual_genome, x, y, raw_time,
                    mouse_speed, mouse_distance, inactivity
                )
                img[j, i] = [int(r * 255), int(g * 255), int(b * 255)]
        return img
    
    def render_dual_animation_frames(self,
                                     dual_genome: DualGenome,
                                     resolution: int = 256,
                                     num_frames: int = 30,
                                     time_range: Tuple[float, float] = (0.0, 1.0),
                                     mouse_speed: float = 0.0,
                                     mouse_distance: float = 0.0,
                                     inactivity: float = 0.0) -> list:
        """
        Render multiple frames for a dual CPPN animation.
        raw_time sweeps over time_range; time-signal CPPN is applied per frame.
        """
        frames = []
        start_time, end_time = time_range
        for frame_idx in range(num_frames):
            raw_t = start_time + (end_time - start_time) * (frame_idx / max(1, num_frames - 1))
            frame = self.render_dual_image(
                dual_genome, resolution, raw_time=raw_t,
                mouse_speed=mouse_speed, mouse_distance=mouse_distance, inactivity=inactivity
            )
            frames.append(frame)
        return frames
    
    def save_genome(self, genome: neat.DefaultGenome, filepath: str, visualize: bool = False):
        """
        Save a genome to file.
        
        Args:
            genome: NEAT genome to save
            filepath: Path for .pkl file
            visualize: If True, also creates a network visualization PNG
        """
        with open(filepath, 'wb') as f:
            pickle.dump(genome, f)
        
        # Optionally create visualization
        if visualize:
            viz_path = filepath.replace('.pkl', '_network.pdf')
            try:
                from genome_visualizer import GenomeVisualizer
                visualizer = GenomeVisualizer(self.config)
                visualizer.visualize_genome(genome, viz_path)
            except ImportError as e:
                print(f"Warning: Could not visualize genome. Install matplotlib: pip install matplotlib")
            except Exception as e:
                print(f"Warning: Genome visualization failed: {e}")
   
    def load_genome(self, filepath: str) -> neat.DefaultGenome:
        """Load a genome from file."""
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    
    def mutate_genome(self, genome: neat.DefaultGenome) -> neat.DefaultGenome:
        """Create a mutated copy of a visual genome (legacy support)."""
        return self._mutate_single_genome(genome, self.config)
    
    def _mutate_single_genome(self, 
                              genome: neat.DefaultGenome, 
                              config: neat.Config) -> neat.DefaultGenome:
        """Create a mutated copy of a single genome."""
        # Ensure parent has fitness (required for configure_crossover)
        if genome.fitness is None:
            genome.fitness = 0.0
        
        # Ensure parent has a valid key
        parent_key = genome.key if genome.key is not None else 0
        child = neat.DefaultGenome(parent_key + 1)
        child.configure_crossover(genome, genome, config.genome_config)
        child.mutate(config.genome_config)
        child.fitness = None  # Reset fitness
        return child
    
    def mutate_dual_genome(self, dual_genome: DualGenome, new_key: int) -> DualGenome:
        """Create a mutated copy of a dual genome (both visual and time signal)."""
        visual_child = self._mutate_single_genome(dual_genome.visual, self.config)
        time_child = self._mutate_single_genome(dual_genome.time_signal, self.time_config)
        
        return DualGenome(
            visual=visual_child,
            time_signal=time_child,
            key=new_key
        )
    
    def crossover_genomes(self, 
                         genome1: neat.DefaultGenome, 
                         genome2: neat.DefaultGenome) -> neat.DefaultGenome:
        """Create offspring from two visual genomes (legacy support)."""
        return self._crossover_single_genomes(genome1, genome2, self.config)
    
    def _crossover_single_genomes(self,
                                  genome1: neat.DefaultGenome,
                                  genome2: neat.DefaultGenome,
                                  config: neat.Config) -> neat.DefaultGenome:
        """Create offspring from two single genomes."""
        # Ensure parents have fitness (required for configure_crossover)
        if genome1.fitness is None:
            genome1.fitness = 0.0
        if genome2.fitness is None:
            genome2.fitness = 0.0
        
        # Ensure parents have valid keys
        key1 = genome1.key if genome1.key is not None else 0
        key2 = genome2.key if genome2.key is not None else 0
        child = neat.DefaultGenome(max(key1, key2) + 1)
        child.configure_crossover(genome1, genome2, config.genome_config)
        child.fitness = None  # Reset fitness
        return child
    
    def crossover_dual_genomes(self,
                               dual1: DualGenome,
                               dual2: DualGenome,
                               new_key: int) -> DualGenome:
        """Create offspring from two dual genomes."""
        visual_child = self._crossover_single_genomes(
            dual1.visual, dual2.visual, self.config
        )
        time_child = self._crossover_single_genomes(
            dual1.time_signal, dual2.time_signal, self.time_config
        )
        
        return DualGenome(
            visual=visual_child,
            time_signal=time_child,
            key=new_key
        )
    
    def save_dual_genome(self, dual_genome: DualGenome, filepath: str, visualize: bool = False):
        """
        Save a dual genome to file.
        
        Args:
            dual_genome: DualGenome to save
            filepath: Path for .pkl file
            visualize: If True, also creates a network visualization PDF of the visual genome
        """
        with open(filepath, 'wb') as f:
            pickle.dump({
                'visual': dual_genome.visual,
                'time_signal': dual_genome.time_signal,
                'key': dual_genome.key
            }, f)
        
        # Optionally create visualization of the visual genome
        if visualize:
            viz_path = filepath.replace('.pkl', '_network.pdf')
            try:
                from genome_visualizer import GenomeVisualizer
                visualizer = GenomeVisualizer(self.config)
                visualizer.visualize_genome(dual_genome.visual, viz_path)
            except ImportError as e:
                print(f"Warning: Could not visualize genome. Install matplotlib: pip install matplotlib")
            except Exception as e:
                print(f"Warning: Genome visualization failed: {e}")
    
    def load_dual_genome(self, filepath: str) -> DualGenome:
        """Load a dual genome from file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            return DualGenome(
                visual=data['visual'],
                time_signal=data['time_signal'],
                key=data.get('key', 0)
            )


def create_random_genome(config: neat.Config, genome_id: int = 0) -> neat.DefaultGenome:
    """
    Create a random genome with the given configuration.
    
    Args:
        config: NEAT configuration
        genome_id: ID for the genome
        
    Returns:
        Randomly initialized genome
    """
    genome = neat.DefaultGenome(genome_id)
    genome.configure_new(config.genome_config)
    return genome


def create_random_dual_genome(engine: CPPNEngine, genome_id: int = 0) -> DualGenome:
    """
    Create a random dual genome (visual + time signal CPPNs).
    
    Args:
        engine: CPPNEngine instance with both configs loaded
        genome_id: ID for the dual genome
        
    Returns:
        Randomly initialized DualGenome
    """
    visual_genome = create_random_genome(engine.config, genome_id)
    time_genome = create_random_genome(engine.time_config, genome_id)
    
    return DualGenome(
        visual=visual_genome,
        time_signal=time_genome,
        key=genome_id
    )


# ---------------------------------------------------------------------------
# JSON serialization - re-exported from genome_serialization module
# ---------------------------------------------------------------------------
from genome_serialization import (
    genome_to_json,
    genome_from_json,
    dual_genome_to_json,
    dual_genome_from_json,
    copy_genome,
    copy_dual_genome,
)

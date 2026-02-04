"""
CPPN Engine for generating time-varying patterns.
Uses NEAT-Python for evolution.
"""
import neat
import numpy as np
from typing import Tuple, Optional
import pickle
from custom_activations import register_custom_activations


class CPPNEngine:
    """
    Compositional Pattern Producing Network engine.
    Generates time-varying visual patterns using evolved neural networks.
    """
    
    def __init__(self, config_path: str = "neat_config.txt"):
        """Initialize CPPN engine with NEAT configuration."""
        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            config_path
        )
        # Register custom activation functions
        register_custom_activations(self.config)
        self.population = None
        self.generation = 0
        
    def create_population(self) -> neat.Population:
        """Create initial population."""
        self.population = neat.Population(self.config)
        self.population.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        self.population.add_reporter(stats)
        return self.population
    
    def query_cppn(self, 
                   genome: neat.DefaultGenome, 
                   x: float, 
                   y: float, 
                   time: float = 0.0,
                   distance: Optional[float] = None) -> Tuple[float, float, float]:
        """
        Query a CPPN for RGB values at given coordinates and time.
        
        Args:
            genome: NEAT genome to evaluate
            x: X coordinate (normalized -1 to 1)
            y: Y coordinate (normalized -1 to 1)
            time: Time value (normalized -1 to 1)
            distance: Distance from center (computed if None)
            
        Returns:
            RGB values (each 0-1)
        """
        if distance is None:
            distance = np.sqrt(x**2 + y**2)
        
        # CPPN inputs: x, y, distance, time, bias
        inputs = [x, y, distance, time, 1.0]
        
        # Create network and activate
        net = neat.nn.FeedForwardNetwork.create(genome, self.config)
        outputs = net.activate(inputs)
        
        # Clamp outputs to 0-1 range
        r = max(0.0, min(1.0, (outputs[0] + 1.0) / 2.0))
        g = max(0.0, min(1.0, (outputs[1] + 1.0) / 2.0))
        b = max(0.0, min(1.0, (outputs[2] + 1.0) / 2.0))
        
        return r, g, b
    
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
    
    def save_genome(self, genome: neat.DefaultGenome, filepath: str):
        """Save a genome to file."""
        with open(filepath, 'wb') as f:
            pickle.dump(genome, f)
    
    def load_genome(self, filepath: str) -> neat.DefaultGenome:
        """Load a genome from file."""
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    
    def mutate_genome(self, genome: neat.DefaultGenome) -> neat.DefaultGenome:
        """Create a mutated copy of a genome."""
        # Ensure parent has fitness (required for configure_crossover)
        if genome.fitness is None:
            genome.fitness = 0.0
        
        # Ensure parent has a valid key
        parent_key = genome.key if genome.key is not None else 0
        child = neat.DefaultGenome(parent_key + 1)
        child.configure_crossover(genome, genome, self.config.genome_config)
        child.mutate(self.config.genome_config)
        child.fitness = None  # Reset fitness
        return child
    
    def crossover_genomes(self, 
                         genome1: neat.DefaultGenome, 
                         genome2: neat.DefaultGenome) -> neat.DefaultGenome:
        """Create offspring from two parent genomes."""
        # Ensure parents have fitness (required for configure_crossover)
        if genome1.fitness is None:
            genome1.fitness = 0.0
        if genome2.fitness is None:
            genome2.fitness = 0.0
        
        # Ensure parents have valid keys
        key1 = genome1.key if genome1.key is not None else 0
        key2 = genome2.key if genome2.key is not None else 0
        child = neat.DefaultGenome(max(key1, key2) + 1)
        child.configure_crossover(genome1, genome2, self.config.genome_config)
        child.fitness = None  # Reset fitness
        return child


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

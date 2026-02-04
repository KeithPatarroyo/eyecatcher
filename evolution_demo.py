"""
Interactive Evolution Demo
Simulates user selection and breeding of patterns
"""
from cppn_engine import CPPNEngine, create_random_genome
from shader_compiler import ShaderCompiler
from PIL import Image
import numpy as np
import os
import random


class InteractiveEvolution:
    """
    Simulates interactive evolutionary art system.
    In a real system, users would pick favorites visually.
    Here we use a simple fitness function as a proxy.
    """
    
    def __init__(self, population_size: int = 16):
        self.engine = CPPNEngine()
        self.engine.create_population()
        self.population_size = population_size
        self.generation = 0
        self.population = []
        self.compiler = ShaderCompiler()
        
    def initialize_population(self):
        """Create initial random population."""
        print(f"Initializing population of {self.population_size}...")
        self.population = []
        for i in range(self.population_size):
            genome = create_random_genome(self.engine.config, genome_id=i)
            self.population.append(genome)
        print(f"Created {len(self.population)} random genomes")
    
    def render_population(self, time: float = 0.5, resolution: int = 128):
        """Render all genomes in the population."""
        images = []
        for genome in self.population:
            img = self.engine.render_image(genome, resolution, time)
            images.append(img)
        return images
    
    def simple_fitness(self, genome) -> float:
        """
        Simple aesthetic fitness function.
        In real system, this would be user selection.
        
        This function rewards:
        - Color variety
        - Spatial complexity
        - Temporal variation
        """
        # Sample at a few points and times
        samples = []
        coords = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
        times = [0.2, 0.5, 0.8]
        
        for t in times:
            for x, y in coords:
                r, g, b = self.engine.query_cppn(genome, x, y, t)
                samples.append([r, g, b])
        
        samples = np.array(samples)
        
        # Color variety (higher variance = more interesting)
        color_variance = np.var(samples)
        
        # Temporal change (patterns should change over time)
        temporal_samples = []
        for t in times:
            r, g, b = self.engine.query_cppn(genome, 0, 0, t)
            temporal_samples.append([r, g, b])
        temporal_variance = np.var(temporal_samples)
        
        # Combined fitness
        fitness = color_variance * 10 + temporal_variance * 5
        
        # Penalty for all-black or all-white
        mean_color = np.mean(samples)
        if mean_color < 0.1 or mean_color > 0.9:
            fitness *= 0.5
        
        return fitness
    
    def select_parents(self, num_parents: int = 4):
        """
        Select top genomes based on fitness.
        In real system, users would click their favorites.
        """
        # Evaluate fitness for all genomes
        fitness_scores = []
        for genome in self.population:
            fitness = self.simple_fitness(genome)
            fitness_scores.append((genome, fitness))
        
        # Sort by fitness
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top parents
        parents = [genome for genome, _ in fitness_scores[:num_parents]]
        
        print(f"Selected {num_parents} parents with fitness: ", end="")
        print([f"{score:.3f}" for _, score in fitness_scores[:num_parents]])
        
        return parents
    
    def breed_new_generation(self, parents: list, num_offspring: int = None):
        """
        Create new generation through mutation and crossover.
        """
        if num_offspring is None:
            num_offspring = self.population_size
        
        new_population = []
        offspring_count = 0
        
        # Keep best parent (elitism)
        new_population.append(parents[0])
        offspring_count += 1
        
        # Generate offspring
        while offspring_count < num_offspring:
            # Randomly choose operation: mutate (70%) or crossover (30%)
            if random.random() < 0.7:
                # Mutation: pick random parent and mutate
                parent = random.choice(parents)
                child = self.engine.mutate_genome(parent)
            else:
                # Crossover: pick two random parents
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)
                child = self.engine.crossover_genomes(parent1, parent2)
            
            new_population.append(child)
            offspring_count += 1
        
        self.population = new_population
        self.generation += 1
        
        print(f"Generated {len(new_population)} offspring (Gen {self.generation})")
    
    def save_generation(self, output_dir: str, time: float = 0.5):
        """Save images of current generation."""
        gen_dir = os.path.join(output_dir, f"gen_{self.generation:03d}")
        os.makedirs(gen_dir, exist_ok=True)
        
        images = self.render_population(time=time)
        
        for i, (genome, img) in enumerate(zip(self.population, images)):
            # Save image
            img_path = os.path.join(gen_dir, f"pattern_{i:02d}.png")
            Image.fromarray(img, 'RGB').save(img_path)
            
            # Save genome
            genome_path = os.path.join(gen_dir, f"genome_{i:02d}.pkl")
            self.engine.save_genome(genome, genome_path)
        
        print(f"Saved generation {self.generation} to {gen_dir}")
    
    def save_best_as_shader(self, output_path: str):
        """Export best genome as shader."""
        parents = self.select_parents(num_parents=1)
        best = parents[0]
        
        shader_code = self.compiler.compile_to_glsl(best, self.engine.config)
        
        with open(output_path, 'w') as f:
            f.write(shader_code)
        
        print(f"Exported best genome as shader: {output_path}")
    
    def evolve(self, num_generations: int = 5, output_dir: str = "output/evolution"):
        """
        Run full evolution cycle.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize
        self.initialize_population()
        self.save_generation(output_dir)
        
        # Evolve
        for gen in range(num_generations):
            print(f"\n--- Generation {gen + 1}/{num_generations} ---")
            
            # Select best
            parents = self.select_parents(num_parents=4)
            
            # Breed new generation
            self.breed_new_generation(parents)
            
            # Save results
            self.save_generation(output_dir)
        
        # Export best as shader
        shader_path = os.path.join(output_dir, "best_pattern.glsl")
        self.save_best_as_shader(shader_path)
        
        print(f"\n{'='*60}")
        print(f"Evolution complete! {num_generations} generations")
        print(f"Results saved to: {output_dir}")
        print(f"{'='*60}")


def demo_evolution():
    """Run evolution demo."""
    print("=" * 60)
    print("INTERACTIVE EVOLUTION DEMO")
    print("=" * 60)
    print("\nThis demo simulates user selection and breeding.")
    print("In a real system, users would pick their favorites visually.")
    print("Here we use a fitness function as a proxy.\n")
    
    # Create evolution system
    evo = InteractiveEvolution(population_size=12)
    
    # Run evolution
    evo.evolve(num_generations=5, output_dir="output/evolution")


def demo_animation_evolution():
    """Generate animation from evolved pattern."""
    print("\n" + "=" * 60)
    print("ANIMATION FROM EVOLVED PATTERN")
    print("=" * 60)
    
    # Quick evolution to get an interesting pattern
    evo = InteractiveEvolution(population_size=8)
    evo.initialize_population()
    
    # Evolve a few generations
    for _ in range(3):
        parents = evo.select_parents(num_parents=3)
        evo.breed_new_generation(parents)
    
    # Get best genome
    parents = evo.select_parents(num_parents=1)
    best = parents[0]
    
    # Generate animation
    print("\nGenerating animation frames...")
    frames = evo.engine.render_animation_frames(
        best,
        resolution=256,
        num_frames=30,
        time_range=(0.0, 1.0)
    )
    
    # Save frames
    anim_dir = "output/evolved_animation"
    os.makedirs(anim_dir, exist_ok=True)
    
    for i, frame in enumerate(frames):
        Image.fromarray(frame, 'RGB').save(
            os.path.join(anim_dir, f"frame_{i:03d}.png")
        )
    
    print(f"Saved {len(frames)} animation frames to {anim_dir}")
    print("Tip: Use ffmpeg to create video:")
    print(f"  ffmpeg -i {anim_dir}/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4")


if __name__ == "__main__":
    # Run evolution demo
    demo_evolution()
    
    # Generate animation from evolved pattern
    demo_animation_evolution()

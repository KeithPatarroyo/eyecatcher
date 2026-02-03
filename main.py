"""
Eyecatcher - Time-varying CPPN Evolution Demo
Demonstrates CPPN generation and shader compilation
"""
from cppn_engine import CPPNEngine, create_random_genome
from shader_compiler import ShaderCompiler
from PIL import Image
import numpy as np
import os


def save_image(img_array: np.ndarray, filepath: str):
    """Save numpy array as image."""
    img = Image.fromarray(img_array, 'RGB')
    img.save(filepath)
    print(f"Saved: {filepath}")


def demo_static_pattern():
    """Generate a static pattern from a random CPPN."""
    print("\n=== Demo 1: Static Pattern ===")
    
    engine = CPPNEngine()
    engine.create_population()
    
    # Create a random genome
    genome = create_random_genome(engine.config, genome_id=1)
    
    # Render at time=0.5
    img = engine.render_image(genome, resolution=512, time=0.5)
    
    # Save
    os.makedirs("output", exist_ok=True)
    save_image(img, "output/static_pattern.png")


def demo_animation():
    """Generate animation frames from a CPPN."""
    print("\n=== Demo 2: Animation Frames ===")
    
    engine = CPPNEngine()
    engine.create_population()
    
    # Create a random genome
    genome = create_random_genome(engine.config, genome_id=2)
    
    # Render multiple time steps
    frames = engine.render_animation_frames(
        genome, 
        resolution=256, 
        num_frames=10,
        time_range=(0.0, 1.0)
    )
    
    # Save frames
    os.makedirs("output/frames", exist_ok=True)
    for i, frame in enumerate(frames):
        save_image(frame, f"output/frames/frame_{i:03d}.png")
    
    print(f"Generated {len(frames)} frames")


def demo_shader_compilation():
    """Compile a CPPN to GLSL shader code."""
    print("\n=== Demo 3: Shader Compilation ===")
    
    engine = CPPNEngine()
    engine.create_population()
    
    # Create a random genome
    genome = create_random_genome(engine.config, genome_id=3)
    
    # Compile to shader
    compiler = ShaderCompiler()
    shader_code = compiler.compile_to_glsl(genome, engine.config)
    
    # Save shader
    os.makedirs("output", exist_ok=True)
    with open("output/pattern.glsl", 'w') as f:
        f.write(shader_code)
    
    print("Shader code saved to: output/pattern.glsl")
    print("\nShader Preview:")
    print("-" * 60)
    print(shader_code[:500] + "...")
    print("-" * 60)
    
    # Also save as bundle
    compiler.export_shader_bundle(genome, engine.config, "output/pattern_bundle.json")
    print("Shader bundle saved to: output/pattern_bundle.json")


def demo_mutation():
    """Demonstrate genome mutation."""
    print("\n=== Demo 4: Mutation ===")
    
    engine = CPPNEngine()
    engine.create_population()
    
    # Create parent genome
    parent = create_random_genome(engine.config, genome_id=10)
    
    # Render parent
    parent_img = engine.render_image(parent, resolution=256, time=0.5)
    
    # Create mutations
    os.makedirs("output/mutations", exist_ok=True)
    save_image(parent_img, "output/mutations/parent.png")
    
    for i in range(5):
        child = engine.mutate_genome(parent)
        child_img = engine.render_image(child, resolution=256, time=0.5)
        save_image(child_img, f"output/mutations/child_{i}.png")
    
    print("Generated parent and 5 mutations")


def demo_crossover():
    """Demonstrate genome crossover."""
    print("\n=== Demo 5: Crossover ===")
    
    engine = CPPNEngine()
    engine.create_population()
    
    # Create two parent genomes
    parent1 = create_random_genome(engine.config, genome_id=20)
    parent2 = create_random_genome(engine.config, genome_id=21)
    
    # Render parents
    os.makedirs("output/crossover", exist_ok=True)
    p1_img = engine.render_image(parent1, resolution=256, time=0.5)
    p2_img = engine.render_image(parent2, resolution=256, time=0.5)
    save_image(p1_img, "output/crossover/parent1.png")
    save_image(p2_img, "output/crossover/parent2.png")
    
    # Create offspring
    for i in range(3):
        child = engine.crossover_genomes(parent1, parent2)
        child_img = engine.render_image(child, resolution=256, time=0.5)
        save_image(child_img, f"output/crossover/offspring_{i}.png")
    
    print("Generated 2 parents and 3 offspring")


if __name__ == "__main__":
    print("=" * 60)
    print("EYECATCHER - Time-Varying CPPN Evolution")
    print("=" * 60)
    
    # Run all demos
    demo_static_pattern()
    demo_animation()
    demo_shader_compilation()
    demo_mutation()
    demo_crossover()
    
    print("\n" + "=" * 60)
    print("All demos complete! Check the 'output' folder.")
    print("=" * 60)

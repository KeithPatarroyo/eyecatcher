"""
Batch evolution demo using dual-CPPN (visual + time signal).
Simulates automated evolution with a proxy fitness function.
Run from repo root: python demos/evolution_batch.py
"""
import os
import random

import numpy as np
from PIL import Image

from eyecatcher.cppn_engine import (
    CPPNEngine,
    DualGenome,
    create_random_dual_genome,
    copy_dual_genome,
)
from eyecatcher.shader_compiler import ShaderCompiler


def simple_fitness(engine: CPPNEngine, dual_genome: DualGenome) -> float:
    """
    Proxy fitness: color variety and temporal variation via query_dual_cppn.
    In the real system, fitness is user selection (clicks).
    """
    samples = []
    coords = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0, 0)]
    times = [0.2, 0.5, 0.8]
    for t in times:
        raw_t = -1.0 + t * 2.0
        for x, y in coords:
            r, g, b = engine.query_dual_cppn(
                dual_genome, x, y, raw_t,
                mouse_speed=0.0, mouse_distance=0.0, inactivity=0.0
            )
            samples.append([r, g, b])
    samples = np.array(samples)
    color_variance = np.var(samples)
    temporal_samples = []
    for t in times:
        raw_t = -1.0 + t * 2.0
        r, g, b = engine.query_dual_cppn(
            dual_genome, 0, 0, raw_t,
            mouse_speed=0.0, mouse_distance=0.0, inactivity=0.0
        )
        temporal_samples.append([r, g, b])
    temporal_variance = np.var(temporal_samples)
    fitness = color_variance * 10 + temporal_variance * 5
    mean_color = np.mean(samples)
    if mean_color < 0.1 or mean_color > 0.9:
        fitness *= 0.5
    return fitness


def run_evolution(
    population_size: int = 12,
    num_generations: int = 5,
    output_dir: str = "output/evolution",
):
    os.makedirs(output_dir, exist_ok=True)
    engine = CPPNEngine()
    engine.create_population()
    compiler = ShaderCompiler()
    population = []
    genome_counter = 0
    for i in range(population_size):
        dual = create_random_dual_genome(engine, genome_id=genome_counter)
        genome_counter += 1
        population.append(dual)

    for gen in range(num_generations):
        scores = [(d, simple_fitness(engine, d)) for d in population]
        scores.sort(key=lambda x: x[1], reverse=True)
        parents = [d for d, _ in scores[:4]]
        print(f"Gen {gen + 1}/{num_generations} best fitness: {scores[0][1]:.3f}")

        # Save gen images (best few)
        gen_dir = os.path.join(output_dir, f"gen_{gen:03d}")
        os.makedirs(gen_dir, exist_ok=True)
        for idx, (dual, _) in enumerate(scores[:4]):
            img = engine.render_dual_image(dual, resolution=128, raw_time=0.0)
            path = os.path.join(gen_dir, f"pattern_{idx:02d}.png")
            Image.fromarray(img, "RGB").save(path)

        # Breed: elitism + offspring
        best = parents[0]
        genome_counter = max(g.key for g in population) + 1
        new_pop = [copy_dual_genome(best, engine, genome_counter)]
        genome_counter += 1
        while len(new_pop) < population_size:
            if random.random() < 0.7:
                p = random.choice(parents)
                child = engine.mutate_dual_genome(p, genome_counter)
            else:
                p1, p2 = random.sample(parents, 2)
                child = engine.crossover_dual_genomes(p1, p2, genome_counter)
            genome_counter += 1
            new_pop.append(child)
        population = new_pop

    # Export best as dual shader
    scores = [(d, simple_fitness(engine, d)) for d in population]
    scores.sort(key=lambda x: x[1], reverse=True)
    best = scores[0][0]
    shader_path = os.path.join(output_dir, "best_pattern.glsl")
    shader_code = compiler.compile_dual_to_glsl(
        best, engine.config, engine.time_config
    )
    with open(shader_path, "w") as f:
        f.write(shader_code)
    print(f"Saved best shader: {shader_path}")
    print(f"Results in: {output_dir}")


if __name__ == "__main__":
    print("Batch evolution (dual-CPPN) – proxy fitness, no UI")
    run_evolution(population_size=12, num_generations=5)

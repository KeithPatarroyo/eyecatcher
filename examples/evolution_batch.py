"""
Batch evolution demo — substrate-agnostic.

Uses EXPERIMENT_CONFIG (or default) to select substrate. Supports dual_cppn,
single_cppn, and ca. Fitness is pluggable via --fitness.

Run from repo root:
  python examples/evolution_batch.py
  python examples/evolution_batch.py --fitness color_variance
  EXPERIMENT_CONFIG=ca python examples/evolution_batch.py --fitness ca_symmetry
  EXPERIMENT_CONFIG=single python examples/evolution_batch.py --fitness color_variance
"""

import argparse
import json
import os

import numpy as np
from eyecatcher.evaluation.fitness import get_fitness, list_fitness
from eyecatcher.evolution import (
    CROSSOVER_PROBABILITY,
    DEFAULT_POPULATION_SIZE,
    PREVIEW_RENDER_RESOLUTION,
    config,
)
from eyecatcher.evolution.reproduction import produce_next_generation
from PIL import Image


def _render_for_save(substrate, ind):
    """Render individual to image array for saving."""
    img = substrate.render_to_image(ind, resolution=PREVIEW_RENDER_RESOLUTION)
    if img is not None:
        return img
    out = substrate.evaluate(ind, {})
    if out.output_type == "grid" and hasattr(out.data, "shape"):
        arr = np.asarray(out.data)
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
        if arr.dtype != np.uint8:
            arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
        return arr
    return np.zeros((256, 256, 3), dtype=np.uint8)


def run_evolution(
    population_size: int = DEFAULT_POPULATION_SIZE,
    num_generations: int = 5,
    output_dir: str = "output/evolution",
    fitness_name: str = "combined",
):
    substrate = config.get_configured_substrate()
    fitness_fn = get_fitness(fitness_name)
    if fitness_fn is None:
        raise ValueError(
            f"Unknown fitness: {fitness_name}. Available: {', '.join(list_fitness())}"
        )

    print(f"Substrate: {substrate.id}, fitness: {fitness_name}")

    os.makedirs(output_dir, exist_ok=True)
    population = []
    for i in range(population_size):
        ind = substrate.create_random(key=i)
        population.append(ind)

    for gen in range(num_generations):
        scores = [(ind, fitness_fn(ind, substrate)) for ind in population]
        scores.sort(key=lambda x: x[1], reverse=True)
        parents = [ind for ind, _ in scores[:4]]
        print(f"Gen {gen + 1}/{num_generations} best fitness: {scores[0][1]:.3f}")

        # Save gen images (best few)
        gen_dir = os.path.join(output_dir, f"gen_{gen:03d}")
        os.makedirs(gen_dir, exist_ok=True)
        for idx, (ind, _) in enumerate(scores[:4]):
            img_arr = _render_for_save(substrate, ind)
            img = Image.fromarray(img_arr, "RGB")
            path = os.path.join(gen_dir, f"pattern_{idx:02d}.png")
            img.save(path)

        # Breed: use produce_next_generation
        parents_data = [
            {"genome": substrate.to_json(p), "clicks": 1} for i, p in enumerate(parents)
        ]
        children = produce_next_generation(
            substrate,
            parents_data,
            population_size=population_size,
            elitism=True,
            crossover_probability=CROSSOVER_PROBABILITY,
        )
        population = [substrate.from_json(c) for c in children]

    # Export best
    scores = [(ind, fitness_fn(ind, substrate)) for ind in population]
    scores.sort(key=lambda x: x[1], reverse=True)
    best = scores[0][0]
    shader = substrate.compile_to_shader(best)
    if shader:
        shader_path = os.path.join(output_dir, "best_pattern.glsl")
        with open(shader_path, "w") as f:
            f.write(shader)
        print(f"Saved best shader: {shader_path}")
    genome_path = os.path.join(output_dir, "best_genome.json")
    with open(genome_path, "w") as f:
        json.dump(substrate.to_json(best), f, indent=2)
    print(f"Saved best genome: {genome_path}")
    print(f"Results in: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch evolution (substrate-agnostic)")
    parser.add_argument(
        "--fitness",
        default="combined",
        help=f"Fitness function. Available: {', '.join(list_fitness())}",
    )
    parser.add_argument(
        "--generations", type=int, default=5, help="Number of generations"
    )
    parser.add_argument("--population", type=int, default=None, help="Population size")
    parser.add_argument("--output", default="output/evolution", help="Output directory")
    args = parser.parse_args()

    pop_size = args.population or DEFAULT_POPULATION_SIZE
    print("Batch evolution – substrate from EXPERIMENT_CONFIG, proxy fitness")
    run_evolution(
        population_size=pop_size,
        num_generations=args.generations,
        output_dir=args.output,
        fitness_name=args.fitness,
    )

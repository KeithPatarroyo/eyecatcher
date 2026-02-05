"""
VLM-based automated evolution for CPPN patterns.

Uses CLIP embeddings and open-endedness scores to automatically
select and breed interesting patterns without human intervention.
"""
import os
import json
import random
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image

from cppn_engine import (
    CPPNEngine,
    DualGenome,
    create_random_dual_genome,
    copy_dual_genome,
    dual_genome_to_json,
    dual_genome_from_json,
)
from rollout import (
    rollout_population,
    RolloutResult,
)
from asal_metrics import (
    calc_open_endedness_score,
    calc_illumination_score,
    select_top_k,
)


@dataclass
class EvolutionConfig:
    """Configuration for VLM-based evolution."""

    # Population settings
    population_size: int = 12
    num_generations: int = 20

    # Selection settings
    top_k: int = 3  # Number of top patterns to select for breeding
    selection_temperature: float = 0.1  # Randomness in selection (0 = deterministic)

    # Video rollout settings
    num_frames: int = 16  # Frames per animation
    resolution: int = 224  # Image resolution (224 for CLIP)
    time_range: Tuple[float, float] = (0.0, 1.0)

    # Breeding settings
    mutation_rate: float = 0.7  # Probability of mutation vs crossover
    elitism: bool = True  # Keep best parent in next generation

    # Output settings
    output_dir: str = "output/vlm_evolution"
    save_every: int = 1  # Save images every N generations
    save_all_frames: bool = False  # Save all animation frames (can be large)

    # Model settings
    clip_model: str = "openai/clip-vit-base-patch32"


@dataclass
class GenerationResult:
    """Result of a single generation."""
    generation: int
    scores: np.ndarray  # Open-endedness scores for each individual
    selected_indices: np.ndarray  # Indices of selected parents
    best_score: float
    mean_score: float
    population_keys: List[int] = field(default_factory=list)


class VLMEvolution:
    """
    Automated evolution using VLM (Vision Language Model) for fitness.

    Uses CLIP embeddings and open-endedness metrics to automatically
    select and breed interesting patterns.
    """

    def __init__(self, config: Optional[EvolutionConfig] = None):
        """
        Initialize VLM evolution.

        Parameters
        ----------
        config : EvolutionConfig, optional
            Configuration for evolution. Uses defaults if not provided.
        """
        self.config = config or EvolutionConfig()
        self.engine = CPPNEngine()
        self.engine.create_population()

        # Lazy-load CLIP embedder
        self._embedder = None

        # State
        self.population: List[DualGenome] = []
        self.generation = 0
        self.history: List[GenerationResult] = []
        self.genome_counter = 0

    @property
    def embedder(self):
        """Lazy-load CLIP embedder on first use."""
        if self._embedder is None:
            from foundation_models.clip import CLIPEmbedder
            self._embedder = CLIPEmbedder(
                model_name=self.config.clip_model,
            )
        return self._embedder

    def initialize_population(self, seeds: Optional[List[Dict]] = None):
        """
        Initialize the population with random genomes or seeds.

        Parameters
        ----------
        seeds : list of dict, optional
            Seed genomes in JSON format. If provided, uses these as initial population.
        """
        self.population = []
        self.genome_counter = 0

        if seeds is not None:
            # Use provided seeds
            for seed_json in seeds[: self.config.population_size]:
                dual = dual_genome_from_json(seed_json, self.engine)
                dual.key = self.genome_counter
                self.population.append(dual)
                self.genome_counter += 1

            # Fill remaining with random if needed
            while len(self.population) < self.config.population_size:
                dual = create_random_dual_genome(self.engine, self.genome_counter)
                self.population.append(dual)
                self.genome_counter += 1
        else:
            # Random population
            for _ in range(self.config.population_size):
                dual = create_random_dual_genome(self.engine, self.genome_counter)
                self.population.append(dual)
                self.genome_counter += 1

        self.generation = 0
        self.history = []

    def compute_open_endedness_scores(
        self,
        rollouts: List[RolloutResult],
    ) -> np.ndarray:
        """
        Compute open-endedness scores for each individual.

        Parameters
        ----------
        rollouts : list of RolloutResult
            Video rollouts with CLIP embeddings (as JAX arrays).

        Returns
        -------
        np.ndarray
            Open-endedness scores for each individual (lower = more interesting).
        """
        scores = []
        for rollout in rollouts:
            if rollout.embeddings is not None:
                # Embeddings are already JAX arrays from CLIPEmbedder
                score = calc_open_endedness_score(rollout.embeddings)
                # Convert JAX scalar back to Python float
                score = float(score)
            else:
                # Fallback: high score (not interesting) if no embeddings
                score = 1.0
            scores.append(score)
        return np.array(scores)

    def select_parents(
        self,
        scores: np.ndarray,
    ) -> np.ndarray:
        """
        Select top k parents based on open-endedness scores.

        Parameters
        ----------
        scores : np.ndarray
            Open-endedness scores (lower = better).

        Returns
        -------
        np.ndarray
            Indices of selected parents.
        """
        return select_top_k(
            scores,
            k=self.config.top_k,
            temperature=self.config.selection_temperature,
            lower_is_better=True,  # ASAL: lower open-endedness = more diverse
        )

    def breed_next_generation(
        self,
        selected_indices: np.ndarray,
    ) -> List[DualGenome]:
        """
        Breed the next generation from selected parents.

        Parameters
        ----------
        selected_indices : np.ndarray
            Indices of selected parent genomes.

        Returns
        -------
        list of DualGenome
            New population.
        """
        parents = [self.population[i] for i in selected_indices]

        # Set fitness for parents (needed for crossover)
        for i, parent in enumerate(parents):
            # Lower index = better fitness (selected based on score)
            parent.fitness = len(parents) - i

        new_population = []

        # Elitism: keep best parent
        if self.config.elitism:
            best_parent = parents[0]
            elite = copy_dual_genome(best_parent, self.engine, self.genome_counter)
            new_population.append(elite)
            self.genome_counter += 1

        # Breed children
        while len(new_population) < self.config.population_size:
            if random.random() < self.config.mutation_rate:
                # Mutation: select random parent and mutate
                parent = random.choice(parents)
                child = self.engine.mutate_dual_genome(parent, self.genome_counter)
            else:
                # Crossover: select two parents and combine
                parent1, parent2 = random.sample(parents, 2)
                child = self.engine.crossover_dual_genomes(
                    parent1, parent2, self.genome_counter
                )

            new_population.append(child)
            self.genome_counter += 1

        return new_population

    def run_generation(self) -> GenerationResult:
        """
        Run a single generation of evolution.

        Returns
        -------
        GenerationResult
            Results of this generation.
        """
        print(f"Generation {self.generation + 1}/{self.config.num_generations}")

        # Render video rollouts for entire population
        print("  Rendering video rollouts...")
        rollouts = rollout_population(
            self.engine,
            self.population,
            embedder=self.embedder,
            num_frames=self.config.num_frames,
            resolution=self.config.resolution,
            time_range=self.config.time_range,
        )

        # Compute open-endedness scores
        print("  Computing open-endedness scores...")
        scores = self.compute_open_endedness_scores(rollouts)

        # Select top k parents
        selected_indices = self.select_parents(scores)

        # Record results
        result = GenerationResult(
            generation=self.generation,
            scores=scores,
            selected_indices=selected_indices,
            best_score=scores[selected_indices[0]],
            mean_score=scores.mean(),
            population_keys=[g.key for g in self.population],
        )

        # Print stats
        print(f"  Best score: {result.best_score:.4f}")
        print(f"  Mean score: {result.mean_score:.4f}")
        print(f"  Selected: {list(selected_indices)}")

        # Save outputs if configured
        if self.generation % self.config.save_every == 0:
            self._save_generation_outputs(rollouts, scores, selected_indices)

        # Breed next generation
        print("  Breeding next generation...")
        self.population = self.breed_next_generation(selected_indices)
        self.generation += 1
        self.history.append(result)

        return result

    def run(
        self,
        num_generations: Optional[int] = None,
        seeds: Optional[List[Dict]] = None,
    ) -> List[GenerationResult]:
        """
        Run the full evolution loop.

        Parameters
        ----------
        num_generations : int, optional
            Number of generations to run. Defaults to config value.
        seeds : list of dict, optional
            Initial seed genomes in JSON format.

        Returns
        -------
        list of GenerationResult
            Results from all generations.
        """
        if num_generations is not None:
            self.config.num_generations = num_generations

        # Initialize
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.initialize_population(seeds)

        print(f"\nStarting VLM Evolution")
        print(f"  Population size: {self.config.population_size}")
        print(f"  Generations: {self.config.num_generations}")
        print(f"  Top k selection: {self.config.top_k}")
        print(f"  Output: {self.config.output_dir}\n")

        # Run generations
        for _ in range(self.config.num_generations):
            self.run_generation()

        # Final save
        self._save_final_results()

        return self.history

    def _save_generation_outputs(
        self,
        rollouts: List[RolloutResult],
        scores: np.ndarray,
        selected_indices: np.ndarray,
    ):
        """Save generation outputs (images, genomes, etc.)."""
        gen_dir = os.path.join(
            self.config.output_dir, f"gen_{self.generation:03d}"
        )
        os.makedirs(gen_dir, exist_ok=True)

        # Save images for selected patterns
        for rank, idx in enumerate(selected_indices):
            rollout = rollouts[idx]
            genome = self.population[idx]

            # Save middle frame as representative image
            mid_frame = rollout.frames[len(rollout.frames) // 2]
            img_path = os.path.join(
                gen_dir, f"selected_{rank:02d}_key{genome.key}_score{scores[idx]:.4f}.png"
            )
            Image.fromarray(mid_frame).save(img_path)

            # Save genome JSON
            genome_path = os.path.join(gen_dir, f"genome_{rank:02d}_key{genome.key}.json")
            with open(genome_path, "w") as f:
                json.dump(dual_genome_to_json(genome), f, indent=2)

            # Optionally save all frames
            if self.config.save_all_frames:
                frames_dir = os.path.join(gen_dir, f"frames_{rank:02d}_key{genome.key}")
                os.makedirs(frames_dir, exist_ok=True)
                for t, frame in enumerate(rollout.frames):
                    frame_path = os.path.join(frames_dir, f"frame_{t:03d}.png")
                    Image.fromarray(frame).save(frame_path)

        # Save generation metadata
        meta_path = os.path.join(gen_dir, "metadata.json")
        meta = {
            "generation": self.generation,
            "scores": scores.tolist(),
            "selected_indices": selected_indices.tolist(),
            "best_score": float(scores[selected_indices[0]]),
            "mean_score": float(scores.mean()),
            "population_keys": [g.key for g in self.population],
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def _save_final_results(self):
        """Save final evolution results and summary."""
        # Save evolution history
        history_path = os.path.join(self.config.output_dir, "evolution_history.json")
        history_data = []
        for result in self.history:
            history_data.append({
                "generation": result.generation,
                "best_score": float(result.best_score),
                "mean_score": float(result.mean_score),
                "selected_indices": result.selected_indices.tolist(),
            })
        with open(history_path, "w") as f:
            json.dump(history_data, f, indent=2)

        # Save final population
        final_dir = os.path.join(self.config.output_dir, "final_population")
        os.makedirs(final_dir, exist_ok=True)

        for genome in self.population:
            genome_path = os.path.join(final_dir, f"genome_{genome.key}.json")
            with open(genome_path, "w") as f:
                json.dump(dual_genome_to_json(genome), f, indent=2)

        # Save config
        config_path = os.path.join(self.config.output_dir, "config.json")
        config_data = {
            "population_size": self.config.population_size,
            "num_generations": self.config.num_generations,
            "top_k": self.config.top_k,
            "selection_temperature": self.config.selection_temperature,
            "num_frames": self.config.num_frames,
            "resolution": self.config.resolution,
            "time_range": list(self.config.time_range),
            "mutation_rate": self.config.mutation_rate,
            "elitism": self.config.elitism,
            "clip_model": self.config.clip_model,
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        print(f"\nEvolution complete!")
        print(f"Results saved to: {self.config.output_dir}")


def run_vlm_evolution(
    population_size: int = 12,
    num_generations: int = 20,
    top_k: int = 3,
    output_dir: str = "output/vlm_evolution",
    seeds_path: Optional[str] = None,
) -> List[GenerationResult]:
    """
    Convenience function to run VLM-based evolution.

    Parameters
    ----------
    population_size : int
        Size of the population.
    num_generations : int
        Number of generations to evolve.
    top_k : int
        Number of top patterns to select each generation.
    output_dir : str
        Directory for output files.
    seeds_path : str, optional
        Path to JSON file with seed genomes.

    Returns
    -------
    list of GenerationResult
        Results from all generations.
    """
    config = EvolutionConfig(
        population_size=population_size,
        num_generations=num_generations,
        top_k=top_k,
        output_dir=output_dir,
    )

    # Load seeds if provided
    seeds = None
    if seeds_path is not None:
        with open(seeds_path) as f:
            seeds_data = json.load(f)
            # Handle both list and dict with "seeds" key
            if isinstance(seeds_data, dict) and "seeds" in seeds_data:
                seeds = seeds_data["seeds"]
            elif isinstance(seeds_data, list):
                seeds = seeds_data

    evolution = VLMEvolution(config)
    return evolution.run(seeds=seeds)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run VLM-based evolution")
    parser.add_argument("--population", type=int, default=12, help="Population size")
    parser.add_argument("--generations", type=int, default=20, help="Number of generations")
    parser.add_argument("--top-k", type=int, default=3, help="Number of top patterns to select")
    parser.add_argument("--output", type=str, default="output/vlm_evolution", help="Output directory")
    parser.add_argument("--seeds", type=str, default=None, help="Path to seeds JSON file")

    args = parser.parse_args()

    run_vlm_evolution(
        population_size=args.population,
        num_generations=args.generations,
        top_k=args.top_k,
        output_dir=args.output,
        seeds_path=args.seeds,
    )

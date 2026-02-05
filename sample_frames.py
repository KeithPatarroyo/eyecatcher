"""
Sample frames from dual CPPN animations for LLM-based evolution.

This script creates a population of patterns and renders 64 frames from each,
using only the body clock (time signal CPPN) and raw time - no mouse interactions.
"""
import os
import numpy as np
from PIL import Image

from cppn_engine import CPPNEngine, create_random_dual_genome


def sample_animation_frames(
    output_dir: str = "output/llm_frames",
    population_size: int = 12,
    num_frames: int = 64,
    resolution: int = 128,
    seed: int = None
):
    """
    Create a population and sample frames from each pattern's animation.

    Args:
        output_dir: Directory to save frames
        population_size: Number of patterns to generate
        num_frames: Number of frames to sample per animation
        resolution: Image resolution (width and height)
        seed: Random seed for reproducibility
    """
    if seed is not None:
        np.random.seed(seed)

    print(f"Initializing CPPN Engine...")
    engine = CPPNEngine(
        config_path="config/neat_config.txt",
        time_config_path="config/neat_config_time.txt"
    )
    engine.create_population()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nGenerating {population_size} patterns with {num_frames} frames each...")
    print(f"Resolution: {resolution}x{resolution}")
    print(f"Mouse interactions: DISABLED (only body clock + raw time)")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    # Generate patterns and their frames
    for pattern_idx in range(population_size):
        print(f"\nPattern {pattern_idx + 1}/{population_size}:")

        # Create random dual genome
        dual_genome = create_random_dual_genome(engine, genome_id=pattern_idx)

        # Create pattern directory
        pattern_dir = os.path.join(output_dir, f"pattern_{pattern_idx:02d}")
        os.makedirs(pattern_dir, exist_ok=True)

        # Render frames with NO mouse interaction
        # Only raw time (0 to 1) and body clock are active
        print(f"  Rendering {num_frames} frames...", end=" ", flush=True)

        frames = engine.render_dual_animation_frames(
            dual_genome,
            resolution=resolution,
            num_frames=num_frames,
            time_range=(0.0, 1.0),
            mouse_speed=0.0,      # No mouse speed
            mouse_distance=0.0,   # No mouse distance
            inactivity=0.0        # No activity signal
        )

        # Save frames
        for frame_idx, frame in enumerate(frames):
            frame_path = os.path.join(pattern_dir, f"frame_{frame_idx:03d}.png")
            Image.fromarray(frame).save(frame_path)

        print(f"Done! Saved to {pattern_dir}")

        # Also save genome info
        genome_info = {
            "pattern_id": pattern_idx,
            "visual_nodes": len(dual_genome.visual.nodes),
            "visual_connections": len([c for c in dual_genome.visual.connections.values() if c.enabled]),
            "time_nodes": len(dual_genome.time_signal.nodes),
            "time_connections": len([c for c in dual_genome.time_signal.connections.values() if c.enabled]),
        }
        print(f"  Visual CPPN: {genome_info['visual_nodes']} nodes, {genome_info['visual_connections']} connections")
        print(f"  Time CPPN: {genome_info['time_nodes']} nodes, {genome_info['time_connections']} connections")

        # Save genome for later breeding
        genome_path = os.path.join(pattern_dir, "genome.pkl")
        engine.save_dual_genome(dual_genome, genome_path)

    print("\n" + "=" * 60)
    print(f"Sampling complete!")
    print(f"Total frames: {population_size * num_frames}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    # Create a summary grid image
    create_summary_grid(output_dir, population_size, num_frames)


def create_summary_grid(output_dir: str, population_size: int, num_frames: int):
    """Create a summary grid showing one frame from each pattern."""
    print("\nCreating summary grid...")

    # Use frames at different time points for variety
    sample_indices = [0, num_frames // 4, num_frames // 2, 3 * num_frames // 4]

    # Load sample frames
    sample_frames = []
    for pattern_idx in range(population_size):
        pattern_dir = os.path.join(output_dir, f"pattern_{pattern_idx:02d}")
        # Use middle frame as representative
        frame_path = os.path.join(pattern_dir, f"frame_{num_frames // 2:03d}.png")
        if os.path.exists(frame_path):
            img = Image.open(frame_path)
            sample_frames.append(np.array(img))

    if not sample_frames:
        print("  No frames found for summary grid")
        return

    # Create grid (4 columns)
    cols = 4
    rows = (len(sample_frames) + cols - 1) // cols
    frame_size = sample_frames[0].shape[0]

    grid = np.zeros((rows * frame_size, cols * frame_size, 3), dtype=np.uint8)

    for idx, frame in enumerate(sample_frames):
        row = idx // cols
        col = idx % cols
        grid[row * frame_size:(row + 1) * frame_size,
             col * frame_size:(col + 1) * frame_size] = frame

    grid_path = os.path.join(output_dir, "summary_grid.png")
    Image.fromarray(grid).save(grid_path)
    print(f"  Saved summary grid: {grid_path}")


if __name__ == "__main__":
    sample_animation_frames(
        output_dir="output/llm_frames",
        population_size=12,
        num_frames=64,
        resolution=128,
        seed=42  # For reproducibility
    )

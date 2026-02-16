"""
Video rollout module for CPPN pattern evolution.
Renders animation frames and computes embeddings for open-endedness scoring.
"""
import numpy as np
from typing import List, Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass

from cppn_engine import CPPNEngine, DualGenome


@dataclass
class RolloutResult:
    """Result of a video rollout for a single genome."""
    frames: np.ndarray  # Shape: (T, H, W, C) - animation frames
    embeddings: Optional[Any] = None  # Shape: (T, D) - CLIP embeddings (jnp.ndarray)
    genome_key: int = 0


def render_video_rollout(
    engine: CPPNEngine,
    dual_genome: DualGenome,
    num_frames: int = 16,
    resolution: int = 224,
    time_range: Tuple[float, float] = (0.0, 1.0),
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
) -> np.ndarray:
    """
    Render a video rollout (animation frames) for a dual CPPN genome.

    Parameters
    ----------
    engine : CPPNEngine
        The CPPN engine for rendering.
    dual_genome : DualGenome
        The genome to render.
    num_frames : int
        Number of frames in the animation.
    resolution : int
        Image resolution (224 is optimal for CLIP).
    time_range : tuple
        (start_time, end_time) normalized to [0, 1].
    mouse_speed : float
        Simulated mouse speed (normalized -1 to 1).
    mouse_distance : float
        Simulated mouse distance (normalized -1 to 1).
    inactivity : float
        Simulated inactivity level (normalized -1 to 1).

    Returns
    -------
    np.ndarray
        Animation frames of shape (T, H, W, C) with values in [0, 255].
    """
    frames = engine.render_dual_animation_frames(
        dual_genome,
        resolution=resolution,
        num_frames=num_frames,
        time_range=time_range,
        mouse_speed=mouse_speed,
        mouse_distance=mouse_distance,
        inactivity=inactivity,
    )
    return np.array(frames)


def compute_video_embeddings(
    frames: np.ndarray,
    embedder,
):
    """
    Compute CLIP embeddings for video frames.

    Parameters
    ----------
    frames : np.ndarray
        Animation frames of shape (T, H, W, C) with values in [0, 255].
    embedder : CLIPEmbedder
        CLIP model for computing embeddings.

    Returns
    -------
    jnp.ndarray
        L2-normalized embeddings of shape (T, D).
    """
    # Convert frames to list for batch processing
    frame_list = [frames[t] for t in range(frames.shape[0])]
    embeddings = embedder.embed_images(frame_list)
    return embeddings


def rollout_population(
    engine: CPPNEngine,
    population: List[DualGenome],
    embedder=None,
    num_frames: int = 16,
    resolution: int = 224,
    time_range: Tuple[float, float] = (0.0, 1.0),
    mouse_speed: float = 0.0,
    mouse_distance: float = 0.0,
    inactivity: float = 0.0,
) -> List[RolloutResult]:
    """
    Render video rollouts for an entire population.

    Parameters
    ----------
    engine : CPPNEngine
        The CPPN engine for rendering.
    population : list of DualGenome
        Population of genomes to render.
    embedder : CLIPEmbedder, optional
        CLIP model for computing embeddings. If None, only frames are returned.
    num_frames : int
        Number of frames per animation.
    resolution : int
        Image resolution.
    time_range : tuple
        (start_time, end_time) for animation.
    mouse_speed : float
        Simulated mouse speed.
    mouse_distance : float
        Simulated mouse distance.
    inactivity : float
        Simulated inactivity level.

    Returns
    -------
    list of RolloutResult
        Rollout results for each genome in the population.
    """
    results = []

    for genome in population:
        # Render animation frames
        frames = render_video_rollout(
            engine,
            genome,
            num_frames=num_frames,
            resolution=resolution,
            time_range=time_range,
            mouse_speed=mouse_speed,
            mouse_distance=mouse_distance,
            inactivity=inactivity,
        )

        # Compute embeddings if embedder provided
        embeddings = None
        if embedder is not None:
            embeddings = compute_video_embeddings(frames, embedder)

        results.append(RolloutResult(
            frames=frames,
            embeddings=embeddings,
            genome_key=genome.key,
        ))

    return results


def rollout_with_varying_inputs(
    engine: CPPNEngine,
    dual_genome: DualGenome,
    embedder=None,
    num_frames: int = 16,
    resolution: int = 224,
    time_range: Tuple[float, float] = (0.0, 1.0),
    mouse_speed_range: Tuple[float, float] = (0.0, 0.0),
    mouse_distance_range: Tuple[float, float] = (0.0, 0.0),
    inactivity_range: Tuple[float, float] = (0.0, 0.0),
) -> RolloutResult:
    """
    Render a video rollout with time-varying input signals.

    This allows simulating different interaction patterns over time,
    such as gradually increasing mouse activity.

    Parameters
    ----------
    engine : CPPNEngine
        The CPPN engine for rendering.
    dual_genome : DualGenome
        The genome to render.
    embedder : CLIPEmbedder, optional
        CLIP model for computing embeddings.
    num_frames : int
        Number of frames.
    resolution : int
        Image resolution.
    time_range : tuple
        (start_time, end_time) for raw time.
    mouse_speed_range : tuple
        (start, end) for mouse speed interpolation.
    mouse_distance_range : tuple
        (start, end) for mouse distance interpolation.
    inactivity_range : tuple
        (start, end) for inactivity interpolation.

    Returns
    -------
    RolloutResult
        Frames and optionally embeddings.
    """
    frames = []
    start_time, end_time = time_range
    start_speed, end_speed = mouse_speed_range
    start_dist, end_dist = mouse_distance_range
    start_inact, end_inact = inactivity_range

    for frame_idx in range(num_frames):
        t = frame_idx / max(1, num_frames - 1)

        # Interpolate all input signals
        raw_time = start_time + (end_time - start_time) * t
        mouse_speed = start_speed + (end_speed - start_speed) * t
        mouse_distance = start_dist + (end_dist - start_dist) * t
        inactivity = start_inact + (end_inact - start_inact) * t

        # Render single frame
        frame = engine.render_dual_image(
            dual_genome,
            resolution=resolution,
            raw_time=raw_time,
            mouse_speed=mouse_speed,
            mouse_distance=mouse_distance,
            inactivity=inactivity,
        )
        frames.append(frame)

    frames = np.array(frames)

    # Compute embeddings if embedder provided
    embeddings = None
    if embedder is not None:
        embeddings = compute_video_embeddings(frames, embedder)

    return RolloutResult(
        frames=frames,
        embeddings=embeddings,
        genome_key=dual_genome.key,
    )


def sample_frames_uniform(
    frames: np.ndarray,
    k: int,
) -> np.ndarray:
    """
    Sample k frames uniformly from a video.

    Parameters
    ----------
    frames : np.ndarray
        Animation frames of shape (T, H, W, C).
    k : int
        Number of frames to sample.

    Returns
    -------
    np.ndarray
        Sampled frames of shape (k, H, W, C).
    """
    T = frames.shape[0]
    if k >= T:
        return frames

    indices = np.linspace(0, T - 1, k, dtype=int)
    return frames[indices]


def sample_frames_random(
    frames: np.ndarray,
    k: int,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Sample k frames randomly from a video.

    Parameters
    ----------
    frames : np.ndarray
        Animation frames of shape (T, H, W, C).
    k : int
        Number of frames to sample.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    np.ndarray
        Sampled frames of shape (k, H, W, C).
    """
    if seed is not None:
        np.random.seed(seed)

    T = frames.shape[0]
    if k >= T:
        return frames

    indices = np.random.choice(T, k, replace=False)
    indices = np.sort(indices)
    return frames[indices]

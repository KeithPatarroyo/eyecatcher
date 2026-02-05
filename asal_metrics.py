"""
ASAL (Automated Search for Artificial Life) metrics for open-endedness evaluation.
Based on: https://github.com/SakanaAI/asal

These metrics are used to compute interestingness/open-endedness scores
for evolved CPPN patterns based on their temporal evolution.
"""
import numpy as np
from typing import Optional


def calc_open_endedness_score(z: np.ndarray) -> float:
    """
    Calculate the open-endedness score from ASAL.

    This metric measures temporal diversity by computing pairwise similarities
    between frame embeddings. A lower score indicates more diverse/interesting
    evolution over time (each frame is different from previous frames).

    The score is computed by:
    1. Computing the similarity matrix z @ z.T
    2. Taking the lower triangular portion (excluding diagonal)
    3. For each frame, finding the maximum similarity to any previous frame
    4. Averaging these maximum similarities

    A pattern with high temporal diversity will have low maximum similarities
    (each new frame is different from all previous), resulting in a low score.

    Parameters
    ----------
    z : np.ndarray of shape (T, D)
        L2-normalized latent representations of images over time.
        T is the number of timesteps, D is the embedding dimension.

    Returns
    -------
    float
        Open-endedness score (lower is more diverse/interesting).
    """
    # Compute similarity matrix (cosine similarity since z is L2-normalized)
    kernel = z @ z.T  # Shape: (T, T)

    # Keep only lower triangular (similarities to previous frames)
    # k=-1 excludes the diagonal (self-similarity)
    kernel = np.tril(kernel, k=-1)

    # For each frame (row), find max similarity to any previous frame
    # Then average across all frames
    # Note: First row will be all zeros (no previous frames), contributing 0 to mean
    return kernel.max(axis=-1).mean()


def calc_illumination_score(zs: np.ndarray) -> float:
    """
    Calculate the illumination score from ASAL.

    This metric measures diversity across different individuals/parameters
    by computing pairwise similarities and penalizing high similarities.

    Parameters
    ----------
    zs : np.ndarray of shape (N, D)
        L2-normalized latent representations of images from different
        simulation parameters/individuals.

    Returns
    -------
    float
        Illumination score (lower is more diverse).
    """
    N, D = zs.shape
    kernel = zs @ zs.T  # Shape: (N, N)

    # Set diagonal to -inf to exclude self-similarity
    np.fill_diagonal(kernel, -np.inf)

    # For each individual, find max similarity to any other
    return kernel.max(axis=-1).mean()


def calc_supervised_target_score(z: np.ndarray, z_txt: np.ndarray) -> float:
    """
    Calculate the supervised target score from ASAL.

    This metric measures how well the generated images align with
    target text embeddings over time.

    Parameters
    ----------
    z : np.ndarray of shape (T, D)
        L2-normalized latent representations of images over time.
    z_txt : np.ndarray of shape (T2, D)
        L2-normalized latent representations of text prompts.
        If T2 < T, prompts are repeated to match.

    Returns
    -------
    float
        Supervised target score (lower means better alignment).
        Note: Returns negative of diagonal mean, so minimizing this
        maximizes alignment.
    """
    T, T2 = z.shape[0], z_txt.shape[0]
    assert T % T2 == 0, f"T ({T}) must be divisible by T2 ({T2})"

    # Repeat text embeddings to match image count
    repeat_count = T // T2
    z_txt_expanded = np.tile(z_txt, (repeat_count, 1))

    # Compute alignment (text-to-image similarity)
    kernel = z_txt_expanded @ z.T  # Shape: (T, T)

    # Return negative diagonal mean (minimize to maximize alignment)
    return -np.diag(kernel).mean()


def calc_interestingness_score(
    z: np.ndarray,
    z_txt: Optional[np.ndarray] = None,
    open_endedness_weight: float = 1.0,
    target_weight: float = 0.0,
) -> float:
    """
    Calculate a combined interestingness score.

    This is a convenience function that combines open-endedness and
    optionally supervised target scores.

    Parameters
    ----------
    z : np.ndarray of shape (T, D)
        L2-normalized latent representations of images over time.
    z_txt : np.ndarray of shape (T2, D), optional
        L2-normalized text embeddings for target guidance.
    open_endedness_weight : float
        Weight for open-endedness score (default: 1.0).
    target_weight : float
        Weight for supervised target score (default: 0.0).

    Returns
    -------
    float
        Combined interestingness score (lower is more interesting).
    """
    score = open_endedness_weight * calc_open_endedness_score(z)

    if z_txt is not None and target_weight > 0:
        score += target_weight * calc_supervised_target_score(z, z_txt)

    return score


def select_top_k(
    scores: np.ndarray,
    k: int = 3,
    temperature: float = 0.0,
    lower_is_better: bool = True,
) -> np.ndarray:
    """
    Select top k individuals based on scores, with optional temperature sampling.

    Parameters
    ----------
    scores : np.ndarray of shape (N,)
        Scores for each individual.
    k : int
        Number of individuals to select.
    temperature : float
        Sampling temperature. If 0, deterministic selection.
        Higher temperature = more randomness among top candidates.
    lower_is_better : bool
        If True, lower scores are better (default for ASAL metrics).

    Returns
    -------
    np.ndarray
        Indices of selected individuals.
    """
    if lower_is_better:
        # Sort ascending (best = lowest score first)
        sorted_indices = np.argsort(scores)
    else:
        # Sort descending (best = highest score first)
        sorted_indices = np.argsort(scores)[::-1]

    if temperature == 0.0:
        # Deterministic: return top k
        return sorted_indices[:k]

    # Temperature-based sampling from top candidates
    # Consider top 2*k candidates for sampling pool
    pool_size = min(2 * k, len(scores))
    pool = sorted_indices[:pool_size]
    pool_scores = scores[pool]

    if lower_is_better:
        # Convert to "higher is better" for softmax
        pool_scores = -pool_scores

    # Softmax with temperature
    pool_scores = pool_scores - pool_scores.max()  # Numerical stability
    probs = np.exp(pool_scores / temperature)
    probs = probs / probs.sum()

    # Sample without replacement
    selected = np.random.choice(pool, size=k, replace=False, p=probs)
    return selected

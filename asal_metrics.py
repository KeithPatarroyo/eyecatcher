"""
ASAL (Automated Search for Artificial Life) metrics for open-endedness evaluation.
Based on: https://github.com/SakanaAI/asal

These metrics are used to compute interestingness/open-endedness scores
for evolved CPPN patterns based on their temporal evolution.
"""
import jax
import jax.numpy as jnp

from einops import repeat


def calc_supervised_target_score(z, z_txt):
    """
    Calculates the supervised target score from ASAL.
    The returned score should be minimized, since we add a minus sign here.

    Parameters
    ----------
    z : jnp.ndarray of shape (T, D)
        The latent representation of the images over time.
    z_txt : jnp.ndarray of shape (T2, D)
        The latent representation of the text prompts over time.
    """
    T, T2 = z.shape[0], z_txt.shape[0]
    assert T % T2 == 0
    z_txt = repeat(z_txt, "T2 D -> (k T2) D", k=T // T2)

    kernel = z_txt @ z.T
    return -jnp.diag(kernel).mean()


def calc_supervised_target_softmax_score(z, z_txt, temperature_softmax=0.01):
    """
    Calculates the supervised target score from ASAL with softmax.
    This isn't part of the original ASAL, but it's a useful extension.
    This score helps incentivize the simulation to find unique images for each prompt
    rather than one static image satisfying all prompts.
    The returned score should be minimized.

    Parameters
    ----------
    z : jnp.ndarray of shape (T, D)
        The latent representation of the images over time.
    z_txt : jnp.ndarray of shape (T2, D)
        The latent representation of the text prompts over time.
    temperature_softmax : float
        The temperature for the softmax function. For CLIP, leave it at 0.01,
        since that is default CLIP softmax temperature.
    """
    T, T2 = z.shape[0], z_txt.shape[0]
    assert T % T2 == 0
    z_txt = repeat(z_txt, "T2 D -> (k T2) D", k=T // T2)

    kernel = z_txt @ z.T
    loss_sm1 = jax.nn.softmax(kernel / temperature_softmax, axis=-1)
    loss_sm2 = jax.nn.softmax(kernel / temperature_softmax, axis=-2)
    loss_sm1 = -jnp.log(jnp.diag(loss_sm1))
    loss_sm2 = -jnp.log(jnp.diag(loss_sm2))
    return (loss_sm1.mean() + loss_sm2.mean()) / 2.0


def calc_open_endedness_score(z):
    """
    Calculates the open-endedness score from ASAL.
    The returned score should be minimized.

    Parameters
    ----------
    z : jnp.ndarray of shape (T, D)
        The latent representation of the images over time.
    """
    kernel = z @ z.T
    kernel = jnp.tril(kernel, k=-1)
    return kernel.max(axis=-1).mean()


def calc_illumination_score(zs):
    """
    Calculates the illumination score from ASAL.
    The returned score should be minimized.

    Parameters
    ----------
    zs : jnp.ndarray of shape (N, D)
        The latent representation of the images from different simulation parameters.
    """
    N, D = zs.shape
    kernel = zs @ zs.T
    kernel = jnp.where(jnp.eye(N, dtype=bool), -jnp.inf, kernel)
    return kernel.max(axis=-1).mean()


# ---------------------------------------------------------------------------
# Utility functions for integration with the evolution system
# ---------------------------------------------------------------------------

def calc_interestingness_score(
    z,
    z_txt=None,
    open_endedness_weight: float = 1.0,
    target_weight: float = 0.0,
):
    """
    Calculate a combined interestingness score.

    This is a convenience function that combines open-endedness and
    optionally supervised target scores.

    Parameters
    ----------
    z : jnp.ndarray of shape (T, D)
        L2-normalized latent representations of images over time.
    z_txt : jnp.ndarray of shape (T2, D), optional
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
    scores,
    k: int = 3,
    temperature: float = 0.0,
    lower_is_better: bool = True,
):
    """
    Select top k individuals based on scores, with optional temperature sampling.

    Note: This function uses numpy for compatibility with the evolution system,
    since it needs to return indices for Python list indexing.

    Parameters
    ----------
    scores : array-like of shape (N,)
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
    import numpy as np

    # Convert JAX arrays to numpy if needed
    scores = np.asarray(scores)

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

"""
Genome file persistence: save/load DualGenome to pickle files.

Data layer for genome storage. Edit here when changing where or how genomes
are stored on disk. Used by algorithm.engine and web save flow.
"""

from ..genome.genome import DualGenome


def save_dual_genome_to_path(dual_genome: DualGenome, filepath: str) -> None:
    """
    Write a dual genome to a pickle file.

    Args:
        dual_genome: The dual genome to save.
        filepath: Path for the pickle file.
    """
    import pickle

    with open(filepath, "wb") as f:
        pickle.dump(
            {
                "visual": dual_genome.visual,
                "time_signal": dual_genome.time_signal,
                "key": dual_genome.key,
            },
            f,
        )


def load_dual_genome_from_path(filepath: str) -> DualGenome:
    """
    Load a dual genome from a pickle file.

    Args:
        filepath: Path to the pickle file written by save_dual_genome_to_path.

    Returns:
        The restored DualGenome.
    """
    import pickle

    with open(filepath, "rb") as f:
        data = pickle.load(f)
    return DualGenome(
        visual=data["visual"],
        time_signal=data["time_signal"],
        key=data.get("key", 0),
    )

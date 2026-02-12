"""Shared math helpers."""


def normalize_to_bipolar(val: float) -> float:
    """Map value from [0, 1] to [-1, 1]."""
    return val * 2.0 - 1.0

"""
Evolution parameters: population size, crossover, elitism.

Loaded from config/evolution_defaults.json; run `make generate` to sync
frontend fallbacks. Preset overrides applied via experiment.apply_preset().
Runtime overlay (PATCH /api/config) allows in-memory updates without restart.
"""

import json
import os

_REQUIRED_EVOLUTION_KEYS = (
    "population_size",
    "max_population_size",
    "min_population_size",
    "crossover_probability",
    "elitism_default",
)


def _get_root_dir() -> str:
    from .. import get_root_dir

    return get_root_dir()


def _load_evolution_defaults() -> dict:
    """Load config/evolution_defaults.json. Raises if file or keys missing."""
    root = _get_root_dir()
    path = os.path.join(root, "config", "evolution_defaults.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing config/evolution_defaults.json at {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("evolution_defaults.json must be a JSON object")
    missing = [k for k in _REQUIRED_EVOLUTION_KEYS if k not in data or data[k] is None]
    if missing:
        raise ValueError(f"evolution_defaults.json missing or null keys: {missing}")
    return {k: data[k] for k in _REQUIRED_EVOLUTION_KEYS}


# Load evolution defaults from JSON
_evolution_defaults = _load_evolution_defaults()
DEFAULT_POPULATION_SIZE = _evolution_defaults["population_size"]
MAX_POPULATION_SIZE = _evolution_defaults["max_population_size"]
MIN_POPULATION_SIZE = _evolution_defaults["min_population_size"]
CROSSOVER_PROBABILITY = _evolution_defaults["crossover_probability"]
ELITISM_DEFAULT = _evolution_defaults["elitism_default"]

# -----------------------------------------------------------------------------
# Preset overlay (applied by experiment module when preset is loaded)
# -----------------------------------------------------------------------------
_PRESET_OVERLAY: dict = {}


def apply_preset(preset: dict | None) -> None:
    """
    Override evolution defaults from an experiment preset.
    Called by experiment module when loading config/experiments.json.
    """
    global DEFAULT_POPULATION_SIZE, MAX_POPULATION_SIZE  # noqa: PLW0603
    global CROSSOVER_PROBABILITY, ELITISM_DEFAULT  # noqa: PLW0603

    if not preset or not isinstance(preset, dict):
        return
    if "population_size" in preset and preset["population_size"] is not None:
        DEFAULT_POPULATION_SIZE = preset["population_size"]  # noqa: PLW0603
    if "max_population_size" in preset and preset["max_population_size"] is not None:
        MAX_POPULATION_SIZE = preset["max_population_size"]  # noqa: PLW0603
    if "crossover_probability" in preset and preset["crossover_probability"] is not None:
        CROSSOVER_PROBABILITY = preset["crossover_probability"]  # noqa: PLW0603
    if "elitism_default" in preset and preset["elitism_default"] is not None:
        ELITISM_DEFAULT = preset["elitism_default"]  # noqa: PLW0603


# -----------------------------------------------------------------------------
# Runtime overlay (PATCH /api/config) – no server restart
# -----------------------------------------------------------------------------
_RUNTIME_OVERLAY: dict = {}
_ALLOWED_OVERLAY_KEYS = frozenset(
    {"population_size", "max_population_size", "crossover_probability"}
)


def get_population_size() -> int:
    """Current effective population size (overlay or preset/default)."""
    return _RUNTIME_OVERLAY.get("population_size", DEFAULT_POPULATION_SIZE)


def get_max_population_size() -> int:
    """Current effective max population size (overlay or preset/default)."""
    return _RUNTIME_OVERLAY.get("max_population_size", MAX_POPULATION_SIZE)


def get_crossover_probability() -> float:
    """Current effective crossover probability (overlay or preset/default)."""
    return _RUNTIME_OVERLAY.get("crossover_probability", CROSSOVER_PROBABILITY)


def get_elitism_default() -> bool:
    """Default elitism when evolve request omits elitism."""
    return ELITISM_DEFAULT


def update_runtime_config(updates: dict) -> None:
    """
    Update in-memory experiment parameters (no restart).
    Only keys in _ALLOWED_OVERLAY_KEYS are applied; values are type-checked.
    """
    for key, value in (updates or {}).items():
        if key not in _ALLOWED_OVERLAY_KEYS:
            continue
        if key == "crossover_probability":
            if isinstance(value, (int, float)) and 0 <= value <= 1:
                _RUNTIME_OVERLAY[key] = float(value)
        elif key in ("population_size", "max_population_size"):
            if isinstance(value, int) and value >= 1:
                _RUNTIME_OVERLAY[key] = value

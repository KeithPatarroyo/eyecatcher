"""
Experiment parameters: population size, crossover, elitism, render defaults.

Loaded from config/evolution_defaults.json; run `make generate` to sync
frontend fallbacks. Preset overrides applied via experiment.preset.apply_preset().
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


# Render constants (save/export and preview) – never mutated
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5
PREVIEW_RENDER_RESOLUTION = 256
DEFAULT_NUM_FRAMES = 30

# Runtime overlay keys allowed by PATCH /api/config
_ALLOWED_OVERLAY_KEYS = frozenset(
    {"population_size", "max_population_size", "crossover_probability"}
)


class ExperimentConfig:
    """
    Single source of truth for evolution parameters.

    Loads defaults from config/evolution_defaults.json. Preset overlay is
    applied by preset module; runtime overlay is applied by PATCH /api/config.
    Getters return effective value (runtime overlay > preset > defaults).
    """

    def __init__(self) -> None:
        defaults = _load_evolution_defaults()
        self._population_size = defaults["population_size"]
        self._max_population_size = defaults["max_population_size"]
        self._min_population_size = defaults["min_population_size"]
        self._crossover_probability = defaults["crossover_probability"]
        self._elitism_default = defaults["elitism_default"]
        self._runtime_overlay: dict = {}

    def apply_preset(self, preset: dict | None) -> None:
        """
        Override evolution defaults from an experiment preset.
        Called by preset module when loading config/experiments.json.
        """
        if not preset or not isinstance(preset, dict):
            return
        if "population_size" in preset and preset["population_size"] is not None:
            self._population_size = preset["population_size"]
        if (
            "max_population_size" in preset
            and preset["max_population_size"] is not None
        ):
            self._max_population_size = preset["max_population_size"]
        if (
            "crossover_probability" in preset
            and preset["crossover_probability"] is not None
        ):
            self._crossover_probability = preset["crossover_probability"]
        if "elitism_default" in preset and preset["elitism_default"] is not None:
            self._elitism_default = preset["elitism_default"]

    def update_runtime_config(self, updates: dict | None) -> None:
        """
        Update in-memory experiment parameters (no restart).
        Only keys in _ALLOWED_OVERLAY_KEYS are applied; values are type-checked.
        """
        for key, value in (updates or {}).items():
            if key not in _ALLOWED_OVERLAY_KEYS:
                continue
            if key == "crossover_probability":
                if isinstance(value, (int, float)) and 0 <= value <= 1:
                    self._runtime_overlay[key] = float(value)
            elif key in ("population_size", "max_population_size"):
                if isinstance(value, int) and value >= 1:
                    self._runtime_overlay[key] = value

    def get_population_size(self) -> int:
        """Current effective population size (overlay or preset/default)."""
        return self._runtime_overlay.get("population_size", self._population_size)

    def get_max_population_size(self) -> int:
        """Current effective max population size (overlay or preset/default)."""
        return self._runtime_overlay.get(
            "max_population_size", self._max_population_size
        )

    def get_crossover_probability(self) -> float:
        """Current effective crossover probability (overlay or preset/default)."""
        return self._runtime_overlay.get(
            "crossover_probability", self._crossover_probability
        )

    def get_elitism_default(self) -> bool:
        """Default elitism when evolve request omits elitism."""
        return self._elitism_default

    @property
    def min_population_size(self) -> int:
        """Min population size (from defaults; not overridable at runtime)."""
        return self._min_population_size


# Module-level singleton; preset module applies preset after import
config = ExperimentConfig()


def apply_preset(preset: dict | None) -> None:
    """Delegate to singleton. Used by preset module and re-exports."""
    config.apply_preset(preset)


def get_population_size() -> int:
    """Current effective population size."""
    return config.get_population_size()


def get_max_population_size() -> int:
    """Current effective max population size."""
    return config.get_max_population_size()


def get_crossover_probability() -> float:
    """Current effective crossover probability."""
    return config.get_crossover_probability()


def get_elitism_default() -> bool:
    """Default elitism when evolve request omits elitism."""
    return config.get_elitism_default()


def update_runtime_config(updates: dict | None) -> None:
    """Update in-memory experiment parameters (no restart)."""
    config.update_runtime_config(updates)

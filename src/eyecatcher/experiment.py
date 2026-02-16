"""
Experiment parameters, presets, and representation selection.

Loaded from config/evolution_defaults.json and config/experiments.json
(keyed by EXPERIMENT_CONFIG env). Preset overrides applied at import.
Runtime overlay (PATCH /api/config) allows in-memory updates without restart.
Provides get_configured_representation() and NEAT config paths for CPPN representations.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_REQUIRED_EVOLUTION_KEYS = (
    "population_size",
    "max_population_size",
    "min_population_size",
    "crossover_probability",
    "elitism_default",
)


def _get_root_dir() -> str:
    from . import get_root_dir

    return get_root_dir()


def _load_evolution_defaults() -> dict:
    """Load config/evolution_defaults.json. Raises if file or keys missing."""
    root = Path(_get_root_dir())
    path = root / "config" / "evolution_defaults.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing config/evolution_defaults.json at {path}")
    with path.open(encoding="utf-8") as f:
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
    applied at module load; runtime overlay is applied by PATCH /api/config.
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

    _PRESET_KEYS = (
        "population_size",
        "max_population_size",
        "crossover_probability",
        "elitism_default",
    )

    def apply_preset(self, preset: dict | None) -> None:
        """
        Override evolution defaults from an experiment preset.
        Called at module load when loading config/experiments.json.
        """
        if not preset or not isinstance(preset, dict):
            return
        for key in self._PRESET_KEYS:
            if key in preset and preset[key] is not None:
                setattr(self, f"_{key}", preset[key])

    def update_runtime_config(self, updates: dict | None) -> None:
        """
        Update in-memory experiment parameters (no restart).
        Only keys in _ALLOWED_OVERLAY_KEYS are applied; values are type-checked.
        """
        for key, value in (updates or {}).items():
            if key not in _ALLOWED_OVERLAY_KEYS:
                continue
            if key == "crossover_probability":
                if isinstance(value, int | float) and 0 <= value <= 1:
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


# Module-level singleton; preset applied at import
config = ExperimentConfig()


def apply_preset(preset: dict | None) -> None:
    """Delegate to singleton. Used at module load and re-exports."""
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


def _load_preset_by_name(preset_name: str) -> dict | None:
    """Load a single preset from config/experiments.json. Used for provenance only."""
    root = Path(_get_root_dir())
    path = root / "config" / "experiments.json"
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data.get(preset_name) if isinstance(data, dict) else None


def get_effective_config_with_provenance() -> dict:
    """
    Return effective experiment config with provenance per key.

    Use for "where do I set X?" — run `python -m eyecatcher config --show` or
    GET /api/config?provenance=1. Keys: population_size, max_population_size,
    min_population_size, crossover_probability, elitism_default, representation_id.
    Each value has "value" and "from" (which layer it came from).
    """
    preset_name = os.environ.get("EXPERIMENT_CONFIG", "default").strip() or "default"
    defaults = _load_evolution_defaults()
    preset = _load_preset_by_name(preset_name)

    def source(key: str) -> str:
        if key in config._runtime_overlay:
            return "runtime (PATCH /api/config)"
        if preset and key in preset and preset.get(key) is not None:
            if key not in defaults or preset[key] != defaults.get(key):
                return f"config/experiments.json (preset: {preset_name})"
        return "config/evolution_defaults.json"

    getters = {
        "population_size": config.get_population_size,
        "max_population_size": config.get_max_population_size,
        "crossover_probability": config.get_crossover_probability,
        "elitism_default": config.get_elitism_default,
    }
    result = {
        key: {"value": getter(), "from": source(key)} for key, getter in getters.items()
    }
    result["min_population_size"] = {
        "value": config.min_population_size,
        "from": "config/evolution_defaults.json",
    }
    rep_id = (
        (preset.get("representation") or preset.get("substrate"))
        if preset and isinstance(preset, dict)
        else None
    )
    from .representation.registry import DEFAULT_REPRESENTATION_ID

    result["representation_id"] = {
        "value": rep_id or DEFAULT_REPRESENTATION_ID,
        "from": (
            f"config/experiments.json (preset: {preset_name})"
            if rep_id
            else "default (no preset or key)"
        ),
    }
    return result


# -----------------------------------------------------------------------------
# NEAT config paths (CPPN representations only) – may be overridden by preset
# -----------------------------------------------------------------------------
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"


def _load_experiment_preset() -> dict | None:
    """Load preset from config/experiments.json. Returns None if not found."""
    preset_name = os.environ.get("EXPERIMENT_CONFIG", "default").strip()
    if not preset_name:
        return None
    root = Path(_get_root_dir())
    path = root / "config" / "experiments.json"
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        return None
    except json.JSONDecodeError:
        return None
    return data.get(preset_name) if isinstance(data, dict) else None


def _apply_experiment_preset() -> None:
    """Apply preset: override experiment config and NEAT paths."""
    global NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH  # noqa: PLW0603

    preset = _load_experiment_preset()
    config.apply_preset(preset)
    if not preset or not isinstance(preset, dict):
        return
    if "neat_config_path" in preset and preset["neat_config_path"]:
        NEAT_CONFIG_PATH = preset["neat_config_path"]  # noqa: PLW0603
    if "neat_time_config_path" in preset and preset["neat_time_config_path"]:
        NEAT_TIME_CONFIG_PATH = preset["neat_time_config_path"]  # noqa: PLW0603


_apply_experiment_preset()


def get_configured_representation():
    """
    Return the representation instance for the current experiment preset.

    Uses EXPERIMENT_CONFIG / config/experiments.json; preset must set "representation".
    Defaults to DEFAULT_REPRESENTATION_ID if no preset or key.
    """
    from .representation.registry import DEFAULT_REPRESENTATION_ID, get_representation

    preset = _load_experiment_preset()
    if preset and isinstance(preset, dict):
        representation_id = preset.get("representation")
        if representation_id is None:
            representation_id = DEFAULT_REPRESENTATION_ID
        return get_representation(representation_id, **preset)
    return get_representation(DEFAULT_REPRESENTATION_ID)


def warn_if_neat_pop_size_mismatch(representation) -> None:
    """
    At startup/deployment: log a warning if the representation uses NEAT and
    NEAT pop_size differs from our effective population_size.
    """
    neat_pop = representation.get_neat_pop_size()
    if neat_pop is None:
        return
    our_pop = config.get_population_size()
    if neat_pop != our_pop:
        logger.warning(
            "NEAT pop_size (%s) != evolution population_size (%s); "
            "population size is controlled by evolution_defaults.json / preset / UI.",
            neat_pop,
            our_pop,
        )

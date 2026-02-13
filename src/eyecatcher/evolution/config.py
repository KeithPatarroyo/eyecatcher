"""
Evolution constants and NEAT config paths.

Substrate-agnostic evolution params (population_size, crossover_probability, etc.)
are loaded from config/evolution_defaults.json; run `make generate` to sync
frontend fallbacks. Preset overrides come from config/experiments.json.
Render resolution and NEAT config paths stay here (separate concerns).
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Render config (not evolution; used for save/export)
# -----------------------------------------------------------------------------
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5
PREVIEW_RENDER_RESOLUTION = 256
DEFAULT_NUM_FRAMES = 30

# -----------------------------------------------------------------------------
# NEAT config paths (CPPN substrates only)
# -----------------------------------------------------------------------------
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"

# -----------------------------------------------------------------------------
# Evolution defaults (reproduction/selection) — loaded from evolution_defaults.json
# -----------------------------------------------------------------------------
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


def _load_experiment_preset() -> dict | None:
    """Load preset from config/experiments.json. Returns None if not found."""
    preset_name = os.environ.get("EXPERIMENT_CONFIG", "default").strip()
    if not preset_name:
        return None
    root = _get_root_dir()
    path = os.path.join(root, "config", "experiments.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return data.get(preset_name) if isinstance(data, dict) else None


def _apply_experiment_preset() -> None:
    """Override module constants from config/experiments.json if preset exists."""
    global DEFAULT_POPULATION_SIZE, CROSSOVER_PROBABILITY, MAX_POPULATION_SIZE
    global ELITISM_DEFAULT, NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH

    preset = _load_experiment_preset()
    if not preset:
        return
    if "neat_config_path" in preset:
        NEAT_CONFIG_PATH = preset["neat_config_path"]  # noqa: PLW0603
    if "neat_time_config_path" in preset:
        NEAT_TIME_CONFIG_PATH = preset["neat_time_config_path"]  # noqa: PLW0603
    if "population_size" in preset:
        DEFAULT_POPULATION_SIZE = preset["population_size"]  # noqa: PLW0603
    if "max_population_size" in preset:
        MAX_POPULATION_SIZE = preset["max_population_size"]  # noqa: PLW0603
    if "crossover_probability" in preset:
        CROSSOVER_PROBABILITY = preset["crossover_probability"]  # noqa: PLW0603
    if "elitism_default" in preset:
        ELITISM_DEFAULT = preset["elitism_default"]  # noqa: PLW0603


# Load evolution defaults from JSON, then apply preset overrides
_evolution_defaults = _load_evolution_defaults()
DEFAULT_POPULATION_SIZE = _evolution_defaults["population_size"]
MAX_POPULATION_SIZE = _evolution_defaults["max_population_size"]
MIN_POPULATION_SIZE = _evolution_defaults["min_population_size"]
CROSSOVER_PROBABILITY = _evolution_defaults["crossover_probability"]
ELITISM_DEFAULT = _evolution_defaults["elitism_default"]

_apply_experiment_preset()

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


def get_configured_substrate():
    """
    Return the substrate instance for the current experiment preset.

    Uses EXPERIMENT_CONFIG / config/experiments.json; preset may set "substrate"
    (e.g. "dual_cppn") and pass through kwargs (neat_config_path, etc.).
    Defaults to "dual_cppn" if no preset or substrate key.
    """
    from ..substrate import get_substrate

    preset = _load_experiment_preset()
    if preset:
        substrate_id = preset.get("substrate", "dual_cppn")
        return get_substrate(substrate_id, **preset)
    return get_substrate("dual_cppn")


def warn_if_neat_pop_size_mismatch(substrate) -> None:
    """
    At startup/deployment: log a warning if the substrate uses NEAT and
    NEAT pop_size differs from our effective population_size.
    """
    neat_config = getattr(substrate, "config", None)
    if neat_config is None:
        return
    neat_pop = getattr(neat_config, "pop_size", None)
    if neat_pop is None:
        return
    our_pop = get_population_size()
    if neat_pop != our_pop:
        logger.warning(
            "NEAT pop_size (%s) != evolution population_size (%s); "
            "population size is controlled by evolution_defaults.json / preset / UI.",
            neat_pop,
            our_pop,
        )

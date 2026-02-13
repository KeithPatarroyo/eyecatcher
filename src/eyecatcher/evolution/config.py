"""
Evolution constants and NEAT config paths.

Single place for researchers to change population size, crossover rate,
render resolution, and which NEAT config files are used. NEAT config file
names live in config/neat/; see that folder's README for which are default
vs alternatives.

Experiment presets: set EXPERIMENT_CONFIG to a preset name (e.g. experiment_a)
to use paths and settings from config/experiments.json. One restart per
experiment. If unset, the "default" preset is used when the file exists.

CROSSOVER_PROBABILITY: when producing each offspring from two+ parents, probability
of crossover (sexual) vs mutate-one-parent (asexual). Gene-level mutation rates
(weight, bias, activation, etc.) are in the NEAT config files under config/neat/.

Frontend static/js/evolution/evolution_config.js mirrors DEFAULT_POPULATION_SIZE
and MAX_POPULATION_SIZE; update both when changing.
"""

import json
import os

# -----------------------------------------------------------------------------
# Built-in defaults (used when no preset or key missing in preset)
# -----------------------------------------------------------------------------
DEFAULT_POPULATION_SIZE = 12
CROSSOVER_PROBABILITY = 0.3
MAX_POPULATION_SIZE = 50
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"
PREVIEW_RENDER_RESOLUTION = 256
DEFAULT_NUM_FRAMES = 30


def _load_experiment_preset() -> dict | None:
    """Load preset from config/experiments.json. Returns None if not found."""
    from .. import get_root_dir

    preset_name = os.environ.get("EXPERIMENT_CONFIG", "default").strip()
    if not preset_name:
        return None
    root = get_root_dir()
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
    global NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH

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


_apply_experiment_preset()


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

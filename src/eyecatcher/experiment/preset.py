"""
Experiment presets and representation selection.

Loads config/experiments.json (keyed by EXPERIMENT_CONFIG env).
Provides get_configured_representation() and NEAT config paths for CPPN representations.
"""

import json
import logging
import os

from . import config

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# NEAT config paths (CPPN representations only) – may be overridden by preset
# -----------------------------------------------------------------------------
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"


def _get_root_dir() -> str:
    from .. import get_root_dir

    return get_root_dir()


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
    except (Exception, OSError):
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

    Uses EXPERIMENT_CONFIG / config/experiments.json; preset may set "representation"
    or "substrate" (e.g. "dual_cppn") and pass through kwargs (neat_config_path, etc.).
    Defaults to "dual_cppn" if no preset or representation key.
    """
    from ..representation import get_representation

    preset = _load_experiment_preset()
    if preset and isinstance(preset, dict):
        representation_id = preset.get(
            "representation", preset.get("substrate", "dual_cppn")
        )
        return get_representation(representation_id, **preset)
    return get_representation("dual_cppn")


def warn_if_neat_pop_size_mismatch(representation) -> None:
    """
    At startup/deployment: log a warning if the representation uses NEAT and
    NEAT pop_size differs from our effective population_size.
    """
    neat_config = getattr(representation, "config", None)
    if neat_config is None:
        return
    neat_pop = getattr(neat_config, "pop_size", None)
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

"""
Eyecatcher: evolutionary time-varying CPPN patterns with rule generation.

Main API: import from eyecatcher.evolution (config, operators), eyecatcher.genome
(DualGenome, serialization), eyecatcher.signals, eyecatcher.inspection,
eyecatcher.glsl (RuleAssembler). Entrypoint for the web app: eyecatcher.server:app.
"""

__version__ = "0.1.0"

from pathlib import Path

# Repo root when running from source (e.g. development or Docker).
# Package lives at <repo>/src/eyecatcher/; go up two levels to repo root.
_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent.parent


def get_root_dir() -> str:
    """Return the project root directory (for static, config, data paths)."""
    return str(_ROOT_DIR)

"""
Eyecatcher: evolutionary time-varying CPPN patterns with shader generation.

Main API: import from eyecatcher.evolution (config, operators), eyecatcher.genome
(DualGenome, serialization), eyecatcher.signals, eyecatcher.evaluation,
eyecatcher.glsl (ShaderCompiler). Entrypoint for the web app: eyecatcher.server:app.
"""

__version__ = "0.1.0"

import os

# Repo root when running from source (e.g. development or Docker).
# Package lives at <repo>/src/eyecatcher/; go up two levels to repo root.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))


def get_root_dir() -> str:
    """Return the project root directory (for static, config, data paths)."""
    return _ROOT_DIR

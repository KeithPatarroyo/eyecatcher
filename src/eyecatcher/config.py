"""
Named constants and config paths for Eyecatcher.

Single source of truth for:
- App constants (population, breeding, rendering)
- Paths to NEAT config files (evolution parameters live in those .txt files;
  paths are relative to project root.)
"""

# App constants
DEFAULT_POPULATION_SIZE = 12
MUTATION_PROBABILITY = 0.7
MAX_POPULATION_SIZE = 50
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5

# NEAT config file paths (relative to project root)
NEAT_CONFIG_PATH = "config/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat_config_time_experimental.txt"

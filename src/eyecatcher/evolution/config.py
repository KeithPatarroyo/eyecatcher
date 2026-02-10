"""
Evolution constants and NEAT config paths.

Single place for researchers to change population size, mutation probability,
render resolution, and which NEAT config files are used.
"""

# App constants (population, breeding, rendering)
DEFAULT_POPULATION_SIZE = 12
MUTATION_PROBABILITY = 0.7
MAX_POPULATION_SIZE = 50
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5

# NEAT config file paths (relative to project root)
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"

# Preview / batch rendering
PREVIEW_RENDER_RESOLUTION = 256
DEFAULT_NUM_FRAMES = 30

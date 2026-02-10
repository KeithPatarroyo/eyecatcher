"""
Evolution constants and NEAT config paths.

Single place for researchers to change population size, crossover rate,
render resolution, and which NEAT config files are used. NEAT config file
names live in config/neat/; see that folder's README for which are default
vs alternatives.

CROSSOVER_PROBABILITY: when producing each offspring from two+ parents, probability
of crossover (sexual) vs mutate-one-parent (asexual). Gene-level mutation rates
(weight, bias, activation, etc.) are in the NEAT config files under config/neat/.

Frontend static/js/modules/evolution_config.js mirrors DEFAULT_POPULATION_SIZE
and MAX_POPULATION_SIZE; update both when changing.
"""

# App constants (population, breeding, rendering)
DEFAULT_POPULATION_SIZE = 12
# Probability of crossover (two parents) when breeding; else mutate one parent.
# Gene-level mutation rates are in config/neat/*.txt.
CROSSOVER_PROBABILITY = 0.3
MAX_POPULATION_SIZE = 50
DEFAULT_RENDER_RESOLUTION = 512
DEFAULT_RENDER_TIME = 0.5

# NEAT config file paths (relative to project root)
NEAT_CONFIG_PATH = "config/neat/neat_config_experimental.txt"
NEAT_TIME_CONFIG_PATH = "config/neat/neat_config_time_experimental.txt"

# Preview / batch rendering
PREVIEW_RENDER_RESOLUTION = 256
DEFAULT_NUM_FRAMES = 30

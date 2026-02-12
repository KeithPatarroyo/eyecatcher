# NEAT config files

**Default configs:** The app uses by default:

- `neat_config_experimental.txt` – visual CPPN (8 inputs, 3 outputs)
- `neat_config_time_experimental.txt` – time CPPN (5 inputs, 1 output)

**Where paths are set:** Paths are defined in [src/eyecatcher/algorithm/config.py](../../src/eyecatcher/algorithm/config.py) (`NEAT_CONFIG_PATH`, `NEAT_TIME_CONFIG_PATH`). To switch without editing code, use [config/experiments.json](../experiments.json) and set `EXPERIMENT_CONFIG=preset_name` when starting the server.

**Alternatives:** `neat_config.txt` and `neat_config_time.txt` are alternative configs (e.g. different topology or activation options). Use them by updating the two path constants in `algorithm/config.py`.

**Signal counts:** Input/output counts must match the signal registry in [src/eyecatcher/signals/signals.py](../../src/eyecatcher/signals/signals.py) (`VISUAL_INPUTS`, `TIME_INPUTS`, `VISUAL_OUTPUTS`, `TIME_OUTPUTS`). The engine validates this at startup.

**Mutation:** Gene-level mutation rates (`weight_mutate_rate`, `bias_mutate_rate`, `activation_mutate_rate`, etc.) are in these files. The crossover rate (probability of crossover vs mutate-one-parent when producing the next generation) is in [algorithm/config.py](../../src/eyecatcher/algorithm/config.py) as `CROSSOVER_PROBABILITY`.

**Population size:** The app's population size (how many individuals per generation in the UI) is set in [algorithm/config.py](../../src/eyecatcher/algorithm/config.py) (`DEFAULT_POPULATION_SIZE`, `MAX_POPULATION_SIZE`). The `pop_size` in the `[NEAT]` section is used by the NEAT library when creating Population objects; it can be aligned with `MAX_POPULATION_SIZE` for consistency if desired.

# Config and NEAT

**Config overview**

- **neat/** – NEAT algorithm config files (topology, mutation rates). This directory.
- **experiments.json** – Experiment presets. Each preset sets `neat_config_path`, `neat_time_config_path`, `population_size`, `max_population_size`, `crossover_probability`. Start the server with `EXPERIMENT_CONFIG=preset_name` (e.g. `experiment_a`) to use that preset. One restart per experiment.

---

# NEAT config files

**Default configs:** The app uses by default:

- `neat_config_experimental.txt` – visual CPPN (8 inputs, 3 outputs)
- `neat_config_time_experimental.txt` – time CPPN (5 inputs, 1 output)

**Where paths are set:** [experiment/config.py](../../src/eyecatcher/experiment/config.py) or presets in [config/experiments.json](../experiments.json); start with `EXPERIMENT_CONFIG=preset_name` to switch without editing code.

**Signal counts:** Input/output counts must match the representation’s receptors (see [signals/catalog.py](../../src/eyecatcher/signals/catalog.py) and representation receptors). `make generate` runs `generate-neat`, which updates and validates NEAT config against receptor input/output counts.

**Mutation:** Gene-level mutation rates are in these .txt files. Crossover probability and population size: [config/evolution_defaults.json](../evolution_defaults.json) and [experiment/config.py](../../src/eyecatcher/experiment/config.py). See [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md).

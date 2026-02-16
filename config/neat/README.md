# NEAT config

This directory holds NEAT algorithm config files (topology, mutation rates). Experiment presets live in [config/experiments.json](../experiments.json): each preset sets `representation`, and for CPPN/NCA the relevant NEAT path(s). Use `EXPERIMENT_CONFIG=preset_name` (e.g. `default`, `dual`, `nca`) to switch preset; one restart per change.

**Files:**

- **neat_config_experimental.txt**, **neat_config_time_experimental.txt** — dual-CPPN (visual + time).
- **neat_config_nca.txt** — NCA (default representation).
- **neat_config.txt**, **neat_config_time.txt** — single-CPPN.

**Where paths are set:** [experiment.py](../../src/eyecatcher/experiment.py) and presets in [config/experiments.json](../experiments.json).

**Signal counts:** Input/output counts must match the representation's receptors ([signals/catalog.py](../../src/eyecatcher/signals/catalog.py)). Run `make generate` to sync NEAT config and frontend. Population size and crossover: [config/evolution_defaults.json](../evolution_defaults.json). See [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md).

# Config

- **neat/** – NEAT algorithm config files (topology, mutation rates). See neat/README.md.
- **experiments.json** – Experiment presets. Each preset sets `neat_config_path`, `neat_time_config_path`, `population_size`, `max_population_size`, `crossover_probability`. Start the server with `EXPERIMENT_CONFIG=preset_name` (e.g. `experiment_a`) to use that preset. One restart per experiment.

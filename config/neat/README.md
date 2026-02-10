# NEAT config files

**Default configs:** The app uses by default:

- `neat_config_experimental.txt` – visual CPPN (8 inputs, 3 outputs)
- `neat_config_time_experimental.txt` – time CPPN (5 inputs, 1 output)

**Where paths are set:** Paths are defined in [src/eyecatcher/evolution/config.py](../../src/eyecatcher/evolution/config.py) (`NEAT_CONFIG_PATH`, `NEAT_TIME_CONFIG_PATH`). Change those constants to switch to different files in this folder.

**Alternatives:** `neat_config.txt` and `neat_config_time.txt` are alternative configs (e.g. different topology or activation options). Use them by updating the two path constants in `evolution/config.py`.

**Signal counts:** Input/output counts must match the signal registry in [src/eyecatcher/evolution/signals.py](../../src/eyecatcher/evolution/signals.py) (`VISUAL_INPUTS`, `TIME_INPUTS`, `VISUAL_OUTPUTS`, `TIME_OUTPUTS`). The engine validates this at startup.

# Examples

Run any script from repo root: `python examples/<script>.py`. Requires venv and dependencies (see main [README](../README.md)).

- **api_usage.py** – Programmatic API: create engine and dual genome, render image, compile to GLSL, mutate, crossover, save. Good first script to see the evolution API.
- **evolution_batch.py** – Batch evolution with a proxy fitness function (color and temporal variation). Runs several generations and saves the best individual; shows how to use breeding and fitness outside the web UI.
- **time_signal_showcase.py** – Plots modified time vs raw time for a few dual genomes (time CPPN as "heartbeat"). Requires matplotlib.

# Researcher guide

This guide points you to the files that matter for changing evolution behavior (signals, NEAT config, breeding, rendering). The rest of the app (server, community, genealogy UI) you can mostly ignore for evolution-only work.

## Where evolution logic lives

- All evolution code is in **src/eyecatcher/evolution/**.
- Public API: `from eyecatcher.evolution import CPPNEngine, create_random_dual_genome, dual_genome_to_json, ...` (see evolution/__init__.py).
- Entry point for the web app is **server.py**; it uses evolution for compile, breed, save, and query.

## Add or change a signal (input/output)

- **Backend:** [src/eyecatcher/evolution/signals.py](src/eyecatcher/evolution/signals.py) – edit VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS, TIME_OUTPUTS (Signal/Output dataclasses).
- **NEAT:** Update num_inputs/num_outputs in [config/neat/](config/neat/) (e.g. neat_config_experimental.txt, neat_config_time_experimental.txt). Engine validates at startup that these match the registry.
- **Frontend:** [static/js/modules/evolution_config.js](static/js/modules/evolution_config.js) – keep SIGNAL_TOGGLES in sync so the UI and shader get the same inputs. There is a test (test_signal_registry) that checks Python vs JS alignment.

## Change NEAT config paths or population size

- [src/eyecatcher/evolution/config.py](src/eyecatcher/evolution/config.py) – NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH, DEFAULT_POPULATION_SIZE, MUTATION_PROBABILITY, etc. Config files live in [config/neat/](config/neat/); see config/neat/README.md for which are default.

## Breeding and selection

- [src/eyecatcher/evolution/breeding.py](src/eyecatcher/evolution/breeding.py) – `breed_next_generation()` (parent handling, elitism, mutation vs crossover). Called by the server's breed endpoint.
- [src/eyecatcher/evolution/operators.py](src/eyecatcher/evolution/operators.py) – `mutate_dual_genome`, `crossover_dual_genomes`. Change selection or add tournament selection by editing breeding.py and/or operators.

## Rendering (CPU) and serialization

- **Rendering:** [src/eyecatcher/evolution/rendering.py](src/eyecatcher/evolution/rendering.py) – render_dual_image, render_dual_animation_frames (used for save PNG and batch export). Single-CPPN path: render_image, render_animation_frames (tests and legacy).
- **Serialization:** [src/eyecatcher/evolution/serialization.py](src/eyecatcher/evolution/serialization.py) – genome_to_json, dual_genome_to_json, dual_genome_from_json, extract_network_data (for network viz and API).

## GLSL / shader compilation

- [src/eyecatcher/evolution/shader_compiler.py](src/eyecatcher/evolution/shader_compiler.py) – compiles dual CPPN to one GLSL fragment shader. Uses signals.py for input/output names; activation functions are mapped here. Researchers extend activation mapping or output interpretation here.

## What you can ignore for evolution-only work

- **Server and routes:** server.py, stateless_api.py, genealogy_routes.py, community_routes.py – HTTP and DB; you only need to know that they call evolution (breeding, compile, serialization) and engine.
- **Frontend:** static/ – pattern renderer, viewer controls, and evolution_config.js matter for signals and UI; the rest (community UI, genealogy viewer, storage) is optional for "just evolution."
- **Data and config:** data/ (DBs), config/neat/ (file contents matter; paths set in evolution/config.py).

## Quick reference

| I want to… | File(s) |
|------------|---------|
| Add/rename a signal | signals.py, evolution_config.js, NEAT num_inputs/num_outputs |
| Change population size or NEAT paths | evolution/config.py |
| Change breeding/selection | evolution/breeding.py, operators.py |
| Change CPU rendering | evolution/rendering.py |
| Change how CPPN becomes GLSL | evolution/shader_compiler.py |
| Change serialization / network export | evolution/serialization.py |

For full project layout and running the app, see [README.md](README.md). For contributing (tests, style), see [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

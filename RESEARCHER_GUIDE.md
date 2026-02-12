# Researcher guide

This guide points you to the files that matter for changing evolution behavior (signals, NEAT config, reproduction, rendering). The rest of the app (server, community, genealogy UI) you can mostly ignore for evolution-only work.

## How the backend is grouped

The Python package is under `src/eyecatcher/`. Main packages:

| Area | What it is | When you look here |
|------|------------|---------------------|
| **algorithm/** | Config, CPPNEngine, reproduction, operators. | Changing the evolution algorithm or NEAT config. |
| **genome/** | DualGenome, wire serialization (JSON, copy). | Changing genome representation or serialization. |
| **signals/** | Input/output definitions, activation. | Adding/changing signals or activation functions. |
| **evaluation/** | CPU rendering, query, genome_visualizer, network_data (graph/stats for UI/API). | Changing rendering, CPPN evaluation, or network export. |
| **glsl/** | Display pipeline: genome → GLSL. | Changing how genomes become shader code. |
| **web/** | Flask app, routes, response_builder. | Adding endpoints or changing API. |
| **lib/** | DB and path utilities. | Fixing infra. |
| **data/** | Genealogy DB; genome_persistence (pickle save/load). | Changing genealogy or genome file storage. |

Exact file tree and file-by-file roles: **[src/eyecatcher/README.md](src/eyecatcher/README.md)**.

## Where evolution logic lives

- **Public API:** Import from **eyecatcher.algorithm** (CPPNEngine, config), **eyecatcher.genome** (DualGenome, serialization), **eyecatcher.signals**, **eyecatcher.evaluation**, **eyecatcher.glsl** (ShaderCompiler).
- **Algorithm** (config, engine, reproduction, operators): **src/eyecatcher/algorithm/**.
- **Genome and wire serialization:** **src/eyecatcher/genome/**; network graph/stats for UI/API: **src/eyecatcher/evaluation/network_data.py**.
- **Signals and activation:** **src/eyecatcher/signals/**.
- **CPU rendering, query, visualization:** **src/eyecatcher/evaluation/**.
- **Shader pipeline** (genome to GLSL): **src/eyecatcher/glsl/** (display only).
- **Genome file save/load:** **src/eyecatcher/data/genome_persistence.py**.
- **Entry point:** **server.py** at package root; uses algorithm, genome, glsl, etc. for compile, evolve, save, and query.

## Add or change a signal (input/output)

Signals are defined in Python only; the frontend config is generated from the registry.

1. **Edit the registry:** [src/eyecatcher/signals/signals.py](src/eyecatcher/signals/signals.py) – add or change entries in VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS, TIME_OUTPUTS. Use `Signal("id", "Label")` for inputs; use `Signal("id", "Label", is_spatial=True)` for per-pixel inputs (x, y, distance); use `Output("id", "Label")` for outputs.
2. **Generate frontend config:** Run `make generate-signals` (or `python scripts/generate_signal_config.py` from repo root). This writes [static/js/evolution/evolution_config_signals.generated.js](static/js/evolution/evolution_config_signals.generated.js) and validates NEAT config.
3. **NEAT counts:** If you added or removed inputs/outputs, update num_inputs/num_outputs in [config/neat/](config/neat/) (neat_config_experimental.txt, neat_config_time_experimental.txt). The generate script will fail with a clear message if they don’t match the registry.
4. Restart the server and reload the app.

## Change NEAT config paths or population size

- [src/eyecatcher/algorithm/config.py](src/eyecatcher/algorithm/config.py) – NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH, DEFAULT_POPULATION_SIZE, CROSSOVER_PROBABILITY, etc. Config files live in [config/neat/](config/neat/); see config/neat/README.md for which are default. Crossover rate (probability of crossover vs mutate-one-parent when producing next generation) is here; gene-level mutation rates are in the NEAT .txt files.

## Breeding and selection

- [src/eyecatcher/algorithm/reproduction.py](src/eyecatcher/algorithm/reproduction.py) – `produce_next_generation()` (parent handling, elitism, mutation vs crossover). Called by the server's evolve endpoint.
- [src/eyecatcher/algorithm/operators.py](src/eyecatcher/algorithm/operators.py) – `mutate_dual_genome`, `crossover_dual_genomes`. Change selection or add tournament selection by editing reproduction.py and/or operators.

## Rendering (CPU) and serialization

- **Rendering:** [src/eyecatcher/evaluation/rendering.py](src/eyecatcher/evaluation/rendering.py) – render_dual_image, render_dual_animation_frames (used for save PNG and batch export). Single-CPPN path: render_image, render_animation_frames (tests and legacy).
- **Serialization (wire format):** [src/eyecatcher/genome/serialization.py](src/eyecatcher/genome/serialization.py) – genome_to_json, dual_genome_to_json, dual_genome_from_json, copy_*. **Network graph/stats for UI/API:** [src/eyecatcher/evaluation/network_data.py](src/eyecatcher/evaluation/network_data.py) – extract_network_data, dual_genome_network_stats, parse_network_node_id.

## GLSL / shader compilation (display pipeline)

Shaders are how we *display* evolved genomes, not part of the evolution algorithm. The pipeline lives in **glsl/**:

- **Phases:** Topology → node code → template. Implemented in [glsl/compiler_topology.py](src/eyecatcher/glsl/compiler_topology.py) (enabled connections, evaluation order), [glsl/node_code_generator.py](src/eyecatcher/glsl/node_code_generator.py) (genome → GLSL node computations), [glsl/glsl_fragments.py](src/eyecatcher/glsl/glsl_fragments.py) (activation GLSL strings), [glsl/shader_compiler.py](src/eyecatcher/glsl/shader_compiler.py) (orchestrates and builds the full shader).
- **Add an activation:** Register it in [signals/activation.py](src/eyecatcher/signals/activation.py) for CPU query; add the GLSL in [glsl/glsl_fragments.py](src/eyecatcher/glsl/glsl_fragments.py) and the name mapping in [glsl/node_code_generator.py](src/eyecatcher/glsl/node_code_generator.py) (`ACTIVATION_FUNCTIONS`); update NEAT config if needed.
- **Change output (color mode):** Edit `_get_color_output_code()` and `color_mode` in [glsl/shader_compiler.py](src/eyecatcher/glsl/shader_compiler.py).
- **Change inputs/signals:** Edit [signals/signals.py](src/eyecatcher/signals/signals.py) (VISUAL_INPUTS, TIME_INPUTS, build_glsl_input_map); the compiler uses them automatically.

## Shader response (compile / save / export)

The same “shader + network stats” shape is built in one place and used by the compile API, save bundle, and export:

- **Helper:** [src/eyecatcher/web/response_builder.py](src/eyecatcher/web/response_builder.py) – `build_shader_response(dual_genome, *, individual_id, clicks, compiler, visual_config, time_config, extra_metadata=None)`.
- **Returned keys:** `id`, `shader`, `clicks`, `nodes`, `connections`, `visual_nodes`, `visual_connections`, `time_nodes`, `time_connections`. The compile API returns `{ "shaders": [ build_shader_response(...) for each ] }`; save and export use the same stats for bundle metadata.
- **Extending metadata:** Add fields via `extra_metadata` (merged into the result), or extend the helper (e.g. `compile_version`, `compile_time_ms`); then compile, save, and export all expose them consistently.

## Data collection / genealogy

Genealogy stores evolutionary history (populations, individuals, branches) in SQLite:

- **Data layer:** [src/eyecatcher/data/genealogy_db.py](src/eyecatcher/data/genealogy_db.py) – DB init, `save_generation_result`, `save_population`, and pure query functions. [src/eyecatcher/data/genome_persistence.py](src/eyecatcher/data/genome_persistence.py) – `save_dual_genome_to_path`, `load_dual_genome_from_path` (pickle). No Flask; returns Python dicts/lists or genome objects.
- **Routes:** [web/genealogy_routes.py](src/eyecatcher/web/genealogy_routes.py) – thin HTTP wrappers: parse request, call genealogy_db, jsonify.
- **Extending metadata:** The `populations.metadata_json` column stores arbitrary JSON. Pass `metadata={...}` to `save_population` or `save_generation_result` (e.g. experiment_id, config_hash, selection method) for reproducibility; export includes it.
- **Custom export:** Export format is the dict returned by `export_genealogy_data`. To add another format (e.g. CSV of fitness over time), add a function in genealogy_db and a route that calls it.

## Frontend extension points

The viewer frontend is grouped by role; see **[static/js/README.md](static/js/README.md)** for the full layout.

- **evolution/** — Where the experiment lives (signals, reproduction, rendering). Edit when you change how evolution or the viewer behaves: [evolution_config.js](static/js/evolution/evolution_config.js), [evolution_coordinator.js](static/js/evolution/evolution_coordinator.js), [pattern_renderer.js](static/js/evolution/pattern_renderer.js), [viewer_controls.js](static/js/evolution/viewer_controls.js).
- **app/** — Application shell (state, grid, fullscreen, genealogy sync, animation loop). Edit when you change app structure or flow: [app.js](static/js/app/app.js), [population_state.js](static/js/app/population_state.js), etc.
- **lib/** — Infrastructure (API client, utils, toast, storage). Only touch for bugs or app-wide support.
- **features/** — Optional features (population UI, community, network viz, toolbar, genealogy viewer). Edit when you care about that feature.

[static/js/app/app.js](static/js/app/app.js) wires everything and passes state + actions to the feature modules.

## What you can ignore for evolution-only work

- **Server and routes:** server.py, web/ (stateless_api, genealogy_routes, community_routes) – HTTP and DB; they call algorithm (reproduction), genome (serialization), glsl (compile), response_builder, and data (genealogy_db).
- **Frontend:** static/ – pattern renderer, viewer controls, and evolution_config.js matter for signals and UI; the rest (community UI, genealogy viewer, storage) is optional for "just evolution."
- **Data and config:** data/ (DBs), config/neat/ (file contents matter; paths set in algorithm/config.py).

## Keeping frontend in sync

Some constants exist in both Python and JavaScript; when you change them, update both sides. Default dev port: Python uses [server.py](src/eyecatcher/server.py) (`DEFAULT_PORT`); frontend uses [static/js/evolution/evolution_config.js](static/js/evolution/evolution_config.js) (`DEFAULT_DEV_PORT`). Population size and max: [algorithm/config.py](src/eyecatcher/algorithm/config.py) and EvolutionConfig in evolution_config.js. **Signal toggles and outputs** come from the Python registry: run `make generate-signals` after changing [signals/signals.py](src/eyecatcher/signals/signals.py); the generated file is consumed by evolution_config.js. test_signal_registry checks that the generated file matches the registry.

## Quick reference

| I want to… | File(s) |
|------------|---------|
| Add/rename a signal | signals/signals.py, then make generate-signals; update NEAT num_inputs/num_outputs if counts changed |
| Change population size or NEAT paths | algorithm/config.py |
| Change reproduction/selection | algorithm/reproduction.py, algorithm/operators.py |
| Change CPU rendering | evaluation/rendering.py |
| Change how CPPN becomes GLSL | glsl/shader_compiler.py, glsl/glsl_fragments.py, glsl/node_code_generator.py, glsl/compiler_topology.py |
| Change compile/save/export response shape | web/response_builder.py |
| Change genealogy storage or export | data/genealogy_db.py |
| Change wire serialization | genome/serialization.py |
| Change network graph/stats for API or viz | evaluation/network_data.py |
| Change genome file save/load | data/genome_persistence.py |

For full project layout and running the app, see [README.md](README.md). For contributing (tests, style), see [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

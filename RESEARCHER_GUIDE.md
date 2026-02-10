# Researcher guide

This guide points you to the files that matter for changing evolution behavior (signals, NEAT config, breeding, rendering). The rest of the app (server, community, genealogy UI) you can mostly ignore for evolution-only work.

## How the backend is grouped

The Python package uses the same mental model as the frontend ([static/js/README.md](static/js/README.md)):

| Area | What it is | When you look here |
|------|------------|---------------------|
| **evolution/** | The algorithm: genomes, breeding, signals, CPU rendering, serialization. | Changing how evolution works. |
| **glsl/** | Display pipeline: genome → GLSL (shader compiler, topology, node code, fragments). | Changing how genomes become shader code. |
| **web/** | Server, API blueprints, response helpers. | Adding endpoints or changing app wiring. |
| **lib/** | DB and path utilities. | Fixing infra or adding app-wide support. |
| **data/** | Genealogy DB, (community). | Changing genealogy storage, export, or a feature. |

Full file-by-file layout: **[src/eyecatcher/README.md](src/eyecatcher/README.md)**.

## Where evolution logic lives

- The *algorithm* (genomes, breeding, operators, engine, CPU rendering) is in **src/eyecatcher/evolution/**.
- Turning genomes into shader code is in **src/eyecatcher/glsl/** (not part of “evolution” as a concept—it’s the display pipeline).
- Public API: `from eyecatcher.evolution import CPPNEngine, create_random_dual_genome, dual_genome_to_json, ShaderCompiler, ...` (ShaderCompiler re-exported from glsl).
- Entry point for the web app is **server.py**; it uses evolution and glsl for compile, breed, save, and query.

## Add or change a signal (input/output)

- **Backend:** [src/eyecatcher/signals/signals.py](src/eyecatcher/signals/signals.py) – edit VISUAL_INPUTS, TIME_INPUTS, VISUAL_OUTPUTS, TIME_OUTPUTS (Signal/Output dataclasses).
- **NEAT:** Update num_inputs/num_outputs in [config/neat/](config/neat/) (e.g. neat_config_experimental.txt, neat_config_time_experimental.txt). Engine validates at startup that these match the registry.
- **Frontend:** [static/js/evolution/evolution_config.js](static/js/evolution/evolution_config.js) – keep SIGNAL_TOGGLES in sync so the UI and shader get the same inputs. There is a test (test_signal_registry) that checks Python vs JS alignment.

## Change NEAT config paths or population size

- [src/eyecatcher/algorithm/config.py](src/eyecatcher/algorithm/config.py) – NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH, DEFAULT_POPULATION_SIZE, CROSSOVER_PROBABILITY, etc. Config files live in [config/neat/](config/neat/); see config/neat/README.md for which are default. Crossover rate (probability of crossover vs mutate-one-parent when breeding) is here; gene-level mutation rates are in the NEAT .txt files.

## Breeding and selection

- [src/eyecatcher/algorithm/breeding.py](src/eyecatcher/algorithm/breeding.py) – `breed_next_generation()` (parent handling, elitism, mutation vs crossover). Called by the server's breed endpoint.
- [src/eyecatcher/algorithm/operators.py](src/eyecatcher/algorithm/operators.py) – `mutate_dual_genome`, `crossover_dual_genomes`. Change selection or add tournament selection by editing breeding.py and/or operators.

## Rendering (CPU) and serialization

- **Rendering:** [src/eyecatcher/evaluation/rendering.py](src/eyecatcher/evaluation/rendering.py) – render_dual_image, render_dual_animation_frames (used for save PNG and batch export). Single-CPPN path: render_image, render_animation_frames (tests and legacy).
- **Serialization:** [src/eyecatcher/genome/serialization.py](src/eyecatcher/genome/serialization.py) – genome_to_json, dual_genome_to_json, dual_genome_from_json, extract_network_data (for network viz and API).

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

- **Data layer:** [src/eyecatcher/data/genealogy_db.py](src/eyecatcher/data/genealogy_db.py) – DB init, `save_breeding_result`, `save_population`, and pure query functions (`get_population`, `get_tree_nodes`, `get_branches`, `export_genealogy_data`, `export_sizes`, `get_stats`, `get_population_thumbnail`, `reset_genealogy`). No Flask; returns Python dicts/lists.
- **Routes:** [web/genealogy_routes.py](src/eyecatcher/web/genealogy_routes.py) – thin HTTP wrappers: parse request, call genealogy_db, jsonify.
- **Extending metadata:** The `populations.metadata_json` column stores arbitrary JSON. Pass `metadata={...}` to `save_population` or `save_breeding_result` (e.g. experiment_id, config_hash, selection method) for reproducibility; export includes it.
- **Custom export:** Export format is the dict returned by `export_genealogy_data`. To add another format (e.g. CSV of fitness over time), add a function in genealogy_db and a route that calls it.

## Frontend extension points

The viewer frontend is grouped by role; see **[static/js/README.md](static/js/README.md)** for the full layout.

- **evolution/** — Where the experiment lives (signals, breeding, rendering). Edit when you change how evolution or the viewer behaves: [evolution_config.js](static/js/evolution/evolution_config.js), [breed_coordinator.js](static/js/evolution/breed_coordinator.js), [pattern_renderer.js](static/js/evolution/pattern_renderer.js), [viewer_controls.js](static/js/evolution/viewer_controls.js).
- **app/** — Application shell (state, grid, fullscreen, genealogy sync, animation loop). Edit when you change app structure or flow: [app.js](static/js/app/app.js), [population_state.js](static/js/app/population_state.js), etc.
- **lib/** — Infrastructure (API client, utils, toast, storage). Only touch for bugs or app-wide support.
- **features/** — Optional features (population UI, community, network viz, toolbar, genealogy viewer). Edit when you care about that feature.

[static/js/app/app.js](static/js/app/app.js) wires everything and passes state + actions to the feature modules.

## What you can ignore for evolution-only work

- **Server and routes:** server.py, web/ (stateless_api, genealogy_routes, community_routes) – HTTP and DB; they call evolution (breeding, serialization), glsl (compile), response_builder, and data (genealogy_db).
- **Frontend:** static/ – pattern renderer, viewer controls, and evolution_config.js matter for signals and UI; the rest (community UI, genealogy viewer, storage) is optional for "just evolution."
- **Data and config:** data/ (DBs), config/neat/ (file contents matter; paths set in algorithm/config.py).

## Keeping frontend in sync

Some constants exist in both Python and JavaScript; when you change them, update both sides. Default dev port: Python uses [server.py](src/eyecatcher/server.py) (`DEFAULT_PORT`); frontend uses [static/js/evolution/evolution_config.js](static/js/evolution/evolution_config.js) (`DEFAULT_DEV_PORT`). Population size and max: [algorithm/config.py](src/eyecatcher/algorithm/config.py) and EvolutionConfig in evolution_config.js. Signal toggles: [signals/signals.py](src/eyecatcher/signals/signals.py) and SIGNAL_TOGGLES in evolution_config.js (test_signal_registry checks alignment).

## Quick reference

| I want to… | File(s) |
|------------|---------|
| Add/rename a signal | signals/signals.py, evolution_config.js, NEAT num_inputs/num_outputs |
| Change population size or NEAT paths | algorithm/config.py |
| Change breeding/selection | algorithm/breeding.py, algorithm/operators.py |
| Change CPU rendering | evaluation/rendering.py |
| Change how CPPN becomes GLSL | glsl/shader_compiler.py, glsl/glsl_fragments.py, glsl/node_code_generator.py, glsl/compiler_topology.py |
| Change compile/save/export response shape | web/response_builder.py |
| Change genealogy storage or export | data/genealogy_db.py |
| Change serialization / network export | genome/serialization.py |

For full project layout and running the app, see [README.md](README.md). For contributing (tests, style), see [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

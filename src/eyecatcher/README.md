# Backend layout

The Python package is grouped so you can quickly see **what to edit for your experiment** vs **what to leave alone**. The same roles as the frontend ([static/js/README.md](../../static/js/README.md)) apply; we use **evolution/**, **glsl/**, **web/**, **lib/**, **data/**.

---

## **evolution/** — Experiment (the algorithm)

**Edit when you change how evolution works: genomes, breeding, signals, or CPU rendering.**

Shaders are *not* part of evolution as a concept; they’re how we *display* the result. The GLSL pipeline lives in **glsl/**.

| File | Role |
|------|------|
| `signals.py` | Input/output definitions (VISUAL_INPUTS, TIME_INPUTS, build_glsl_input_map). |
| `config.py` | NEAT config paths, population size, crossover rate. |
| `genome.py` | DualGenome, create_random_dual_genome. |
| `breeding.py` | breed_next_generation (elitism, selection, mutation vs crossover). |
| `operators.py` | mutate_dual_genome, crossover_dual_genomes. |
| `activation.py` | CPU activation helpers for query. |
| `engine.py` | CPPNEngine: population, query_time_signal, render_dual_image. |
| `rendering.py` | render_dual_image, render_dual_animation_frames (CPU). |
| `serialization.py` | genome_to_json, dual_genome_to_json, dual_genome_from_json, extract_network_data. |
| `genome_visualizer.py` | Network PDF for genealogy save. |
| `query.py` | CPPN evaluation helpers. |

Public API: `from eyecatcher.evolution import CPPNEngine, create_random_dual_genome, dual_genome_to_json, ShaderCompiler, ...` (see `evolution/__init__.py`; ShaderCompiler is re-exported from glsl).

---

## **glsl/** — Display pipeline (genome → GLSL)

**Edit when you change how a genome becomes shader code or GPU output.**

Evolution produces genomes; this package turns them into fragment shaders for the viewer.

| File | Role |
|------|------|
| `compiler_topology.py` | Enabled connections, topological sort for evaluation order. |
| `node_code_generator.py` | Genome → GLSL node computations; ACTIVATION_FUNCTIONS. |
| `glsl_fragments.py` | Shared GLSL strings (e.g. activation block). |
| `shader_compiler.py` | Compiles dual CPPN to fragment shader (orchestrates the above). |

Import: `from eyecatcher.glsl import ShaderCompiler`.

---

## **web/** — Application & routes (server and HTTP)

**Edit when you change how the app is wired, add endpoints, or change response shape.**

| File | Role |
|------|------|
| `app.py` | Flask app, CORS, blueprints, breed/save handlers, static serve. |
| `stateless_api.py` | Blueprint: /api/compile, /api/random, /api/time-output, /api/network, /api/adjust-weight. |
| `genealogy_routes.py` | Blueprint: save-population, load-population, tree, branches, reset, export, stats, thumbnail. |
| `community_routes.py` | Blueprint: community share/browse/admin. |
| `api_helpers.py` | api_error, error message constants. |
| `response_builder.py` | build_shader_response (single shape for compile, save, export). |

Entry point: `server.py` at package root re-exports `app` from `web.app`; use `eyecatcher.server:app`.

---

## **lib/** — Support (infrastructure)

**Only touch when fixing bugs or adding app-wide support.**

| File | Role |
|------|------|
| `db_util.py` | with_db_connection, default_db_path, sqlite_connection. |

Package root `__init__.py`: `get_root_dir()`, `__version__`.

---

## **data/** — Data & feature layers

**Edit when you care about that feature (genealogy, community, etc.).**

| File | Role |
|------|------|
| `genealogy_db.py` | Genealogy data layer: init, save_breeding_result, save_population, get_population, get_tree_nodes, get_branches, export_genealogy_data, get_stats, get_population_thumbnail, reset_genealogy. No Flask; pure queries. |

Routes in `web/genealogy_routes.py` and `web/community_routes.py` are thin HTTP wrappers.

---

## Summary

| Area | When you look here |
|------|---------------------|
| **evolution/** | Changing the algorithm: signals, breeding, genomes, CPU rendering, serialization. |
| **glsl/** | Changing how genomes become shader code (display pipeline). |
| **web/** | Adding endpoints, changing response shape, or wiring the app. |
| **lib/** | Fixing DB or path helpers, or adding app-wide infra. |
| **data/** | Changing genealogy (or community) storage, export, or metadata. |

For a short “I want to…” table and signal/NEAT/shader details, see the main [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md) in the repo root.

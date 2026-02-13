# Backend layout

This file describes the **actual** layout of `src/eyecatcher/`. Use it to find where to edit for your experiment.

---

## Repository structure

```
src/eyecatcher/
├── __init__.py          # get_root_dir(), __version__
├── server.py            # Entry point: re-exports app from web.app (eyecatcher.server:app)
├── README.md            # This file
│
├── evolution/           # Evolution (config, experiment presets, reproduction, fitness)
│   ├── __init__.py
│   ├── config.py        # evolution params (population_size, crossover, elitism)
│   ├── experiment.py    # get_configured_substrate, NEAT paths, presets
│   ├── fitness.py       # batch fitness (combined, color_variance, …)
│   ├── render_defaults.py
│   └── reproduction.py
│
├── genome/              # NEAT genome: create, serialize, mutate, crossover, activation
│   ├── __init__.py
│   ├── activation.py    # register_custom_activations (e.g. cos)
│   ├── operators.py     # mutate_genome, crossover_genomes
│   └── serialization.py
│
├── signals/             # Input/output signal definitions
│   ├── __init__.py
│   └── registry.py
│
├── inspection/          # Genome viz, network graph/stats for UI/API (look inside genomes)
│   ├── __init__.py
│   ├── genome_graph.py  # layer assignment, output-reachable nodes
│   ├── genome_visualizer.py
│   └── network_data.py  # extract_network_data, parse_network_node_id
│
├── glsl/                # Display pipeline: genome → GLSL fragment shader
│   ├── __init__.py
│   ├── activation_registry.py
│   ├── compiler_topology.py
│   ├── node_code_generator.py
│   └── shader_compiler.py
│
├── web/                 # Flask app and HTTP API (routes, blueprints)
│   ├── __init__.py
│   ├── app.py           # Flask setup, blueprints, save/served routes
│   ├── api_helpers.py
│   ├── community_routes.py
│   ├── evolve_api.py    # /api/evolve + genealogy save
│   ├── genealogy_routes.py
│   └── stateless_api.py
│
└── data/                # Data layers (genealogy DB, db_util)
    ├── __init__.py
    ├── db_util.py
    └── genealogy_db.py
```

---

## Genome types

The codebase uses three genome concepts; each substrate defines its own individual type.

| Location | Type | Used by |
|----------|------|--------|
| **genome/** | NEAT genome primitives: `neat.DefaultGenome`, create/serialize/mutate/crossover, activation registration | CPPN substrates (Single/Dual) |
| **substrate/dual_genome.py** | **DualGenome** — pair of visual + time NEAT genomes | DualCPPNSubstrate |
| **substrate/ca.py** | **ConwayGenome** — 2D grid (rule, state) | ElementaryCASubstrate |

- **genome/** provides shared NEAT building blocks (creation, serialization, operators, custom activations). It does not define “the” individual type for the app.
- Each substrate owns its individual type and how it is serialized to JSON (for the stateless API and client storage). The API “genome” field is substrate-specific; format depends on the active substrate.

---

## What each package is for

| Package | Role | When you look here |
|---------|------|--------------------|
| **evolution/** | NEAT config, reproduction, mutation, crossover, get_configured_substrate. | Changing the evolution algorithm or NEAT config. |
| **genome/** | Generic NEAT genome: create_random_genome, genome_to_json, genome_from_json, copy_genome. | Changing generic genome representation or JSON. |
| **substrate/** | Substrates (Single/ DualCPPN, CA, …), DualGenome, create_random_dual_genome, dual_genome_to_json/from_json, copy_dual_genome. | Changing substrate types or dual-genome serialization. |
| **signals/** | VISUAL_INPUTS, TIME_INPUTS, build_glsl_input_map. | Adding/changing input signals. |
| **inspection/** | genome_visualizer, network_data (extract_network_data for UI/API), genome_graph. Substrates implement render_to_image. | Changing network visualization, API graph/stats, or genome inspection. |
| **glsl/** | ShaderCompiler; topology, node code, GLSL fragments. Genome → fragment shader. | Changing how genomes become shader code (display pipeline). |
| **web/** | Flask app, /api/compile, /api/evolve, /api/save, genealogy routes, community routes, stateless_api. | Adding endpoints or changing API response shape. |
| **data/** | genealogy_db, db_util (with_db_connection, default_db_path). | Changing genealogy storage/export or fixing DB helpers. |

---

## Entry points

- **Flask app:** `eyecatcher.server:app` (root `server.py` re-exports from `web.app`).
- **Public API:** `from eyecatcher.evolution import produce_next_generation, get_configured_substrate, ...`; `from eyecatcher.genome import create_random_genome, genome_to_json, ...`; `from eyecatcher.substrate import DualGenome, get_substrate, create_random_dual_genome, dual_genome_to_json, ...`; `from eyecatcher.glsl import ShaderCompiler`; `from eyecatcher.signals import ...`; `from eyecatcher.inspection import ...`.

---

## Summary

| I want to… | Look in |
|------------|---------|
| Add/rename a signal | signals/registry.py, NEAT config, frontend evolution/config.js |
| Change population size or NEAT paths | evolution/config.py, evolution/experiment.py |
| Change reproduction/selection | evolution/reproduction.py, genome/operators.py |
| Change genome or wire serialization | genome/__init__.py, genome/serialization.py, genome/operators.py |
| Change network graph/stats for UI or API | inspection/network_data.py |
| Change CPU rendering or substrate query | substrate (e.g. cppn_base.evaluate, dual_cppn, ca) |
| Change how CPPN becomes GLSL | glsl/shader_compiler.py, activation_registry.py, node_code_generator.py, compiler_topology.py |
| Change compile/save/export response shape | web/stateless_api.py, substrate get_compile_stats / build_save_assets |
| Change genealogy storage or export | data/genealogy_db.py |
| Change genome bundle save/load (pickle, etc.) | substrate build_save_assets (e.g. dual_cppn) |
| Add an endpoint or change API | web/ (app.py, stateless_api.py, evolve_api.py, genealogy_routes.py, community_routes.py) |

For signal/NEAT/shader details and a short “I want to…” guide, see [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md) in the repo root.

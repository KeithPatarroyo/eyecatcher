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
├── evolution/           # Evolution algorithm (config, reproduction, operators)
│   ├── __init__.py
│   ├── config.py
│   ├── operators.py
│   └── reproduction.py
│
├── genome/              # Genome representation and serialization
│   ├── __init__.py      # create_random_genome + re-exports
│   └── serialization.py
│
├── signals/             # Input/output signal definitions and activation
│   ├── __init__.py
│   ├── activation.py
│   └── registry.py
│
├── evaluation/          # Genome viz, network graph/stats for UI/API, fitness
│   ├── __init__.py
│   ├── fitness.py
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
│   ├── app.py
│   ├── api_helpers.py
│   ├── community_routes.py
│   ├── genealogy_routes.py
│   └── stateless_api.py
│
└── data/                # Data layers (genealogy DB, db_util)
    ├── __init__.py
    ├── db_util.py
    └── genealogy_db.py
```

---

## What each package is for

| Package | Role | When you look here |
|---------|------|--------------------|
| **evolution/** | NEAT config, reproduction, mutation, crossover, get_configured_substrate. | Changing the evolution algorithm or NEAT config. |
| **genome/** | Generic NEAT genome: create_random_genome, genome_to_json, genome_from_json, copy_genome. | Changing generic genome representation or JSON. |
| **substrate/** | Substrates (Single/ DualCPPN, CA, …), DualGenome, create_random_dual_genome, dual_genome_to_json/from_json, copy_dual_genome. | Changing substrate types or dual-genome serialization. |
| **signals/** | VISUAL_INPUTS, TIME_INPUTS, build_glsl_input_map, activation helpers. | Adding/changing input signals or activation functions. |
| **evaluation/** | render_image, query, genome_visualizer, network_data (extract_network_data for UI/API). Substrates implement render_to_image. | Changing CPU rendering, CPPN query, network visualization, or API graph/stats. |
| **glsl/** | ShaderCompiler; topology, node code, GLSL fragments. Genome → fragment shader. | Changing how genomes become shader code (display pipeline). |
| **web/** | Flask app, /api/compile, /api/evolve, /api/save, genealogy routes, community routes, stateless_api. | Adding endpoints or changing API response shape. |
| **data/** | genealogy_db, db_util (with_db_connection, default_db_path). | Changing genealogy storage/export or fixing DB helpers. |

---

## Entry points

- **Flask app:** `eyecatcher.server:app` (root `server.py` re-exports from `web.app`).
- **Public API:** `from eyecatcher.evolution import produce_next_generation, get_configured_substrate, ...`; `from eyecatcher.genome import create_random_genome, genome_to_json, ...`; `from eyecatcher.substrate import DualGenome, get_substrate, create_random_dual_genome, dual_genome_to_json, ...`; `from eyecatcher.glsl import ShaderCompiler`; `from eyecatcher.signals import ...`; `from eyecatcher.evaluation import ...`.

---

## Summary

| I want to… | Look in |
|------------|---------|
| Add/rename a signal | signals/registry.py, NEAT config, frontend evolution/config.js |
| Change population size or NEAT paths | evolution/config.py |
| Change reproduction/selection | evolution/reproduction.py, evolution/operators.py |
| Change genome or wire serialization | genome/__init__.py, genome/serialization.py |
| Change network graph/stats for UI or API | evaluation/network_data.py |
| Change CPU rendering or substrate query | substrate (e.g. cppn_base.evaluate, dual_cppn, ca) |
| Change how CPPN becomes GLSL | glsl/shader_compiler.py, activation_registry.py, node_code_generator.py, compiler_topology.py |
| Change compile/save/export response shape | web/stateless_api.py, substrate get_compile_stats / build_save_assets |
| Change genealogy storage or export | data/genealogy_db.py |
| Change genome bundle save/load (pickle, etc.) | substrate build_save_assets (e.g. dual_cppn) |
| Add an endpoint or change API | web/ (app.py, stateless_api.py, genealogy_routes.py, community_routes.py) |

For signal/NEAT/shader details and a short “I want to…” guide, see [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md) in the repo root.

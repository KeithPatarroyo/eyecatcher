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
├── algorithm/           # Evolution algorithm (config, engine, breeding, operators)
│   ├── __init__.py
│   ├── breeding.py
│   ├── config.py
│   ├── engine.py
│   └── operators.py
│
├── genome/              # Genome representation and serialization
│   ├── __init__.py
│   ├── genome.py
│   └── serialization.py
│
├── signals/             # Input/output signal definitions and activation
│   ├── __init__.py
│   ├── activation.py
│   └── signals.py
│
├── evaluation/          # CPU rendering, query, genome viz, network graph/stats for UI/API
│   ├── __init__.py
│   ├── genome_visualizer.py
│   ├── network_data.py  # extract_network_data, dual_genome_network_stats, parse_network_node_id
│   ├── query.py
│   └── rendering.py
│
├── glsl/                # Display pipeline: genome → GLSL fragment shader
│   ├── __init__.py
│   ├── compiler_topology.py
│   ├── glsl_fragments.py
│   ├── node_code_generator.py
│   └── shader_compiler.py
│
├── web/                 # Flask app and HTTP API (routes, blueprints)
│   ├── __init__.py
│   ├── app.py
│   ├── api_helpers.py
│   ├── community_routes.py
│   ├── genealogy_routes.py
│   ├── response_builder.py
│   └── stateless_api.py
│
├── lib/                 # Infrastructure (DB, paths)
│   ├── __init__.py
│   └── db_util.py
│
└── data/                # Data layers (genealogy, genome file persistence)
    ├── __init__.py
    ├── genealogy_db.py
    └── genome_persistence.py  # save_dual_genome_to_path, load_dual_genome_from_path
```

---

## What each package is for

| Package | Role | When you look here |
|---------|------|--------------------|
| **algorithm/** | NEAT config, CPPNEngine, breeding, mutation, crossover. Engine uses data.genome_persistence for save/load. | Changing the evolution algorithm or NEAT config. |
| **genome/** | DualGenome, create_random_dual_genome, wire serialization (genome_to_json, dual_genome_to_json, copy_*). Network graph/stats re-exported from evaluation. | Changing genome representation or JSON serialization. |
| **signals/** | VISUAL_INPUTS, TIME_INPUTS, build_glsl_input_map, activation helpers. | Adding/changing input signals or activation functions. |
| **evaluation/** | render_dual_image, query, genome_visualizer, network_data (extract_network_data, dual_genome_network_stats for UI/API). | Changing CPU rendering, CPPN query, network visualization, or API graph/stats. |
| **glsl/** | ShaderCompiler; topology, node code, GLSL fragments. Genome → fragment shader. | Changing how genomes become shader code (display pipeline). |
| **web/** | Flask app, /api/compile, /api/breed, /api/save, genealogy routes, community routes, response_builder. | Adding endpoints or changing API response shape. |
| **lib/** | with_db_connection, default_db_path. | Fixing DB or path helpers. |
| **data/** | genealogy_db; genome_persistence (pickle save/load). | Changing genealogy storage, genome file storage, or export. |

---

## Entry points

- **Flask app:** `eyecatcher.server:app` (root `server.py` re-exports from `web.app`).
- **Public API:** `from eyecatcher.algorithm import CPPNEngine, ...`; `from eyecatcher.genome import DualGenome, dual_genome_to_json, ...`; `from eyecatcher.glsl import ShaderCompiler`; `from eyecatcher.signals import ...`; `from eyecatcher.evaluation import ...`.

---

## Summary

| I want to… | Look in |
|------------|---------|
| Add/rename a signal | signals/signals.py, NEAT config, frontend evolution_config.js |
| Change population size or NEAT paths | algorithm/config.py |
| Change breeding/selection | algorithm/breeding.py, algorithm/operators.py |
| Change genome or wire serialization | genome/genome.py, genome/serialization.py |
| Change network graph/stats for UI or API | evaluation/network_data.py |
| Change CPU rendering or query | evaluation/rendering.py, evaluation/query.py |
| Change how CPPN becomes GLSL | glsl/shader_compiler.py, glsl_fragments.py, node_code_generator.py, compiler_topology.py |
| Change compile/save/export response shape | web/response_builder.py |
| Change genealogy storage or export | data/genealogy_db.py |
| Change genome file save/load (pickle) | data/genome_persistence.py |
| Add an endpoint or change API | web/ (app.py, stateless_api.py, genealogy_routes.py, community_routes.py) |

For signal/NEAT/shader details and a short “I want to…” guide, see [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md) in the repo root.

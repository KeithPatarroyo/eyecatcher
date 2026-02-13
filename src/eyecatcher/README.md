# Backend layout

File tree and “where to edit” for `src/eyecatcher/`. Full checklist: **[RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md)** in repo root.

---

## Repository structure

```
src/eyecatcher/
├── __init__.py          # get_root_dir(), __version__
├── server.py            # Entry point: re-exports app from web.app
├── README.md            # This file
│
├── experiment/          # Config, presets, get_configured_representation
│   ├── __init__.py
│   ├── config.py        # evolution params (population_size, crossover, elitism)
│   └── preset.py        # experiment presets, NEAT paths
│
├── evolution/           # Reproduction, fitness
│   ├── __init__.py
│   ├── fitness.py       # batch fitness (combined, color_variance, …)
│   └── reproduction.py  # produce_next_generation
│
├── genome/              # NEAT genome + DualGenome (create, serialize, mutate, crossover)
│   ├── __init__.py
│   ├── activation.py   # register_custom_activations (e.g. cos)
│   ├── creation.py      # create_random_genome
│   ├── dual.py          # DualGenome, dual_genome_to_json/from_json, copy_dual_genome
│   ├── operators.py     # mutate_genome, crossover_genomes
│   └── serialization.py
│
├── representation/      # Representations (Dual/Single CPPN, CA), protocol, sockets
│   ├── __init__.py
│   ├── protocol.py     # Representation protocol, get_representation_capabilities
│   ├── registry.py     # REPRESENTATIONS, get_representation
│   ├── export.py       # export_representations_for_frontend (codegen)
│   ├── sockets.py      # NeatSocket, GridSocket
│   ├── cppn_base.py
│   ├── dual_cppn.py
│   ├── single_cppn.py
│   └── ca.py
│
├── signals/             # Input/output definitions (socket-centric)
│   ├── __init__.py
│   ├── spec.py         # Signal, Output, SignalSpec
│   ├── socket.py       # Socket base
│   ├── catalog.py      # Signal presets (DUAL_CPPN_VISUAL_INPUTS, etc.)
│   └── registry.py      # export_for_frontend, parse_time_inputs
│
├── inspection/          # Genome viz, network graph/stats for UI/API
│   ├── __init__.py
│   ├── genome_graph.py
│   ├── genome_visualizer.py
│   └── network_data.py  # extract_network_data, parse_network_node_id
│
├── glsl/                # Genome → GLSL fragment shader
│   ├── __init__.py
│   ├── activation_registry.py
│   ├── compiler_topology.py
│   ├── node_code_generator.py
│   └── shader_compiler.py
│
├── web/                 # Flask app, routes, stateless API
│   ├── __init__.py
│   ├── app.py
│   ├── api_helpers.py
│   ├── community_routes.py
│   ├── evolve_api.py
│   ├── genealogy_routes.py
│   └── stateless_api.py
│
└── data/                # Genealogy DB, db_util
    ├── __init__.py
    ├── db_util.py
    └── genealogy_db.py
```

---

## Individual types

Each **representation** defines its own individual type and JSON shape. **genome/** provides NEAT primitives and **DualGenome** ([genome/dual.py](genome/dual.py)); **representation/dual_cppn.py**, **single_cppn.py** use them; **representation/ca.py** defines **ConwayGenome**. API "genome" = representation-specific JSON.

---

## Package roles

| Package | Role |
|---------|------|
| **experiment/** | Config, presets, get_configured_representation. |
| **evolution/** | produce_next_generation, fitness. |
| **genome/** | NEAT + DualGenome (create, JSON, mutate, crossover). |
| **representation/** | Protocol, get_representation; Dual/Single CPPN, CA; sockets. |
| **signals/** | Catalog, Socket, SignalSpec; representations use sockets. |
| **inspection/** | genome_visualizer, network_data (graph/stats for API/UI). |
| **glsl/** | Genome → GLSL. **web/** Flask, stateless API. **data/** genealogy_db. |

---

## Entry points

- **Flask:** `eyecatcher.server:app`
- **Imports:** `eyecatcher.experiment` (get_configured_representation), `eyecatcher.evolution` (produce_next_generation, fitness), `eyecatcher.representation` (get_representation, DualGenome, …), `eyecatcher.genome`, `eyecatcher.signals`, `eyecatcher.glsl` (ShaderCompiler)

**Quick reference:** [RESEARCHER_GUIDE.md](../../RESEARCHER_GUIDE.md) in repo root.

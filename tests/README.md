# Test suite

**How to run:** From repo root with venv activated: `make test` or `pytest`. To skip slow tests: `pytest -m "not slow"`.

## What each file tests

| File | Covers |
|------|--------|
| test_cppn_engine.py | Dual-CPPN representation: create_random, evaluate (query), mutate, crossover. |
| test_substrate_compile.py | Representation develop and get_develop_stats (GLSL, node/connection counts). |
| test_genome_serialization.py | Dual-genome serialization: dual_genome_to_json/from_json round-trip, extract_network_data, query consistency. |
| test_shader_compiler.py | GLSL module (glsl.shader_compiler): compile (structure, main, activations, empty connections, single hidden node). |
| test_glsl_validity.py | Generated GLSL sanity: every v_* and *_base used is declared/defined; no redefinition of v_* (shared time/visual signals); dual shader uses _base only for time inputs (catches WebGL compile-time regressions). |
| test_signal_registry.py | Signals module (signals.registry): NEAT config matches registry; frontend evolution_config.js matches Python (toggleable inputs). |
| test_api.py | Flask API: /api/random, /api/develop, /api/express, /api/evolve, /api/save, /api/adjust-weight; uses test client and representation fixtures. |
| test_genealogy_routes.py | Genealogy API: save/load population, tree, branches, export, reset, stats. |
| test_community_routes.py | Community API: submit, list, admin approve/reject. |
| test_visualization.py | Genome visualizer PDF and render_image (single-CPPN). |

## Fixtures (conftest.py)

- **client** – Flask test client (app.test_client() with TESTING=True).
- **representation** – Dual-CPPN representation instance (mutation, crossover, evaluate).
- **random_dual_genome** – One random dual genome (genome_id=0).
- **minimal_dual** – Dual genome with one hidden node in visual CPPN (deterministic).
- **genealogy_db** – Temp DB for genealogy routes; no real data touched.
- **community_db** – Temp DB for community routes; no real data touched.

All DB fixtures use in-memory or temp paths; the real data/ directory is not modified.

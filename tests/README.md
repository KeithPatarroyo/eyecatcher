# Test suite

**How to run:** From repo root with venv activated: `make test` or `pytest`. To skip slow tests: `pytest -m "not slow"`.

## What each file tests

| File | Covers |
|------|--------|
| test_cppn_engine.py | Algorithm engine (algorithm.engine.CPPNEngine): create population, create_random_dual_genome, query_dual_cppn, mutate_dual_genome, crossover_dual_genomes, single-genome path. |
| test_genome_serialization.py | Genome module (genome.serialization): dual_genome_to_json/from_json round-trip, extract_network_data shape, query consistency after round-trip. |
| test_shader_compiler.py | GLSL module (glsl.shader_compiler): compile_dual_to_glsl (structure, main, activations, empty connections, single hidden node). |
| test_glsl_validity.py | Generated GLSL sanity: every v_* and *_base used is declared/defined; no redefinition of v_* (shared time/visual signals); dual shader uses _base only for time inputs (catches WebGL compile-time regressions). |
| test_signal_registry.py | Signals module (signals.signals): NEAT config matches registry; frontend evolution_config.js matches Python (toggleable inputs). |
| test_api.py | Flask API: /api/random, /api/compile, /api/evolve (with/without genealogy), /api/save, save download structure, /api/adjust-weight. Uses test client and cppn_engine/minimal_dual fixtures. |
| test_genealogy_routes.py | Genealogy API: save-population, load-population, tree, branches, export (full and by branch), reset, stats; uses genealogy_db and cppn_engine. |
| test_community_routes.py | Community API: submit, list, admin approve/reject; uses community_db and cppn_engine. |
| test_visualization.py | Genome visualizer PDF and render_image (single-CPPN); uses tmp_path, cppn_engine. |

## Fixtures (conftest.py)

- **client** – Flask test client (app.test_client() with TESTING=True).
- **cppn_engine** – CPPNEngine with population created (for mutation, crossover, query tests).
- **random_dual_genome** – One random dual genome (genome_id=0).
- **minimal_dual** – Dual genome with one hidden node in visual CPPN (deterministic).
- **genealogy_db** – Temp DB for genealogy routes; no real data touched.
- **community_db** – Temp DB for community routes; no real data touched.

All DB fixtures use in-memory or temp paths; the real data/ directory is not modified.

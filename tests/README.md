# Test suite

**How to run:** From repo root with venv activated: `make test` or `pytest`. To skip slow tests: `pytest -m "not slow"`.

## What each file tests

| File | Covers |
|------|--------|
| test_api.py | Flask API: /api/random, /api/develop, /api/express, /api/evolve, /api/save, /api/adjust-weight. |
| test_ca_substrate.py | Conway (CA) representation: create_random, mutate, crossover, express, serialize. |
| test_community_routes.py | Community API: submit, list, admin approve/reject. |
| test_cppn_engine.py | Dual-CPPN: create_random, query, mutate, crossover. |
| test_genome_serialization.py | Dual-genome JSON round-trip, extract_network_data. |
| test_glsl_validity.py | Generated GLSL sanity (slow). |
| test_nca.py | NCA representation: create_random, express, develop, serialize, network inspection. |
| test_representation_refactor.py | NeatEvolvable, GridRepresentationBase, parse_express_options. |
| test_shader_compiler.py | RuleAssembler + develop(): GLSL output. |
| test_signal_registry.py | Signals vs NEAT config and config.generated.js. |
| test_substrate_compile.py | develop() and get_develop_stats (GLSL, node/connection counts). |
| test_visualization.py | Genome visualizer PDF and render_image. |
| test_genealogy_routes.py | Genealogy API: save/load population, tree, export, stats. |

## Fixtures (conftest.py)

- **client** — Flask test client (TESTING=True).
- **representation** — DualCPPN instance (for mutation, crossover, query tests).
- **random_dual_genome**, **minimal_dual** — Dual genomes for CPPN tests.
- **genealogy_db**, **community_db** — Temp DBs; real data/ not modified.

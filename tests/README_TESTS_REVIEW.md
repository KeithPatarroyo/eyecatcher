# Test suite review: robustness vs hacks

This document summarizes a review of the `tests/` folder to distinguish robust tests from weak or hacky ones, and what was fixed.

---

## Summary

| File | Verdict | Notes |
|------|---------|--------|
| **conftest.py** | ✅ Solid | Temp DBs, test client, engine fixture; no hacks. |
| **test_api.py** | ✅ Mostly robust | One test skips when random genome has no visual connections; acceptable. |
| **test_community_routes.py** | ✅ Robust | Clear flow tests, error cases, admin auth. |
| **test_cppn_engine.py** | ⚠️ Had hacks | Trivial assertions in `test_create_random_genome_and_mutate` (fixed). |
| **test_genealogy_routes.py** | ✅ Robust | Save/load round-trip, error cases, tree/branches. |
| **test_genome_serialization.py** | ⚠️ Had weak test | Round-trip “query consistency” didn’t assert same values (fixed). |
| **test_shader_compiler.py** | ⚠️ Had hack | “Single hidden node” relied on 50 random tries then skip (fixed with deterministic genome). |
| **test_visualization.py** | ✅ Acceptable | Integration/smoke test; could add image dimension checks later. |

---

## Details by file

### test_cppn_engine.py

- **test_create_random_genome_and_mutate** (fixed)
  Previously asserted `len(mutated.nodes) >= 0` and `len(mutated.connections) >= 0`, which are always true.
  Now asserts: mutated genome has key = parent_key + 1, and that it has valid structure (nodes/connections dicts, correct key).

- **test_mutate_dual_genome**
  Asserts that the result is a new `DualGenome` with the requested key and that visual/time_signal are new objects. Mutation is probabilistic; the test does not require a structural change, which is correct.

### test_genome_serialization.py

- **test_dual_genome_round_trip_query_consistency** (fixed)
  Docstring said “same-shaped output” but the test only checked that both queries return numbers in 0–255.
  Now also asserts that, for the same inputs, original and restored genomes produce the same RGB values (round-trip fidelity).

### test_shader_compiler.py

- **test_compile_dual_single_hidden_node** (fixed)
  Previously tried up to 50 random genomes hoping for exactly one hidden node, then skipped. That made the test nondeterministic and sometimes a no-op.
  Replaced with a deterministic test: build a minimal dual genome from JSON (visual with exactly one hidden node and one path input→hidden→output), then compile and assert valid GLSL. No randomness, no skip.

### test_api.py

- **test_api_adjust_weight**
  Uses `pytest.skip` when the random genome has no visual connections or missing source/target. That’s acceptable: the test explicitly requires at least one adjustable connection; the skip is documented. Optional improvement: use a fixed seed or a constructed genome to make it always run.

### test_visualization.py

- **test_visualization**
  Integration test: save pkl/txt, render PNG, check files exist and have content. Could be extended later with assertions on image dimensions (e.g. 64×64) or non-empty pixels; not a hack as-is.

---

## Recommendations going forward

1. **Avoid trivial assertions**
   Prefer assertions that would fail if the code regressed (e.g. key increment, structure, or exact values).

2. **Prefer deterministic tests**
   When testing edge cases (e.g. “one hidden node”), construct minimal data (e.g. via JSON) instead of “try N random and skip if not found”.

3. **Round-trip tests**
   For serialize/deserialize, assert that behavior is preserved (e.g. same query output), not only that types or ranges are correct.

4. **Document skips**
   When a test skips due to random data (e.g. no connections), keep the skip reason clear so it’s obvious it’s intentional.

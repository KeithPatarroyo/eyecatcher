# Signals

The **signal registry** (`registry.py`) defines input and output identifiers for CPPN networks.

## Scope: dual-CPPN-centric

The registry is **dual-CPPN-centric**. The names and structure reflect the dual-CPPN representation:

- **VISUAL_INPUTS** / **VISUAL_OUTPUTS** — used by the visual CPPN (spatial + time, mouse, activity).
- **TIME_INPUTS** / **TIME_OUTPUTS** — used by the time-signal CPPN (raw_time, mouse, activity).

Single-CPPN uses only the visual inputs/outputs. The CA representation does not use this registry. Other representations (e.g. NCA, custom topologies) may reuse these as building blocks or define their own signal sets.

## Extending for new representations

If you add a representation that needs different inputs or outputs:

1. **Reuse where it fits** — Compose from `VISUAL_INPUTS`, `TIME_INPUTS`, etc. if your representation shares the same semantics.
2. **Define locally** — Define representation-specific signal lists in your representation module and use them in your config, query, and GLSL logic. The registry stays the single source for dual-CPPN and shared signals; new representations can declare additional signals in their own module.

After changing signal lists used by NEAT (e.g. dual or single CPPN), run `scripts/generate_signal_config.py` to emit the JS config and align NEAT `num_inputs`/`num_outputs`.

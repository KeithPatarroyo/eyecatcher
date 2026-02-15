# Signals

Representation-agnostic vocabulary for inputs and outputs. Signals flow into or out of a representation (NEAT, CA, etc.).

## Architecture

```
signals/
  sensory_system.py  -- Signal, Output, DerivedInput, SensorySystem (receptor-centric)
  receptor.py         -- Receptor (to_array, default_values, input_ids); representation-agnostic binding
  catalog.py          -- Concrete signal instances and presets
  registry.py         -- Helpers (export_for_frontend, parse_time_inputs, etc.)
```

Representation-specific receptor implementations (e.g. `NeatReceptor`) live in **representation/receptors.py**. Representations use receptors for expression; they never touch raw signal lists.

## Extending for new representations

1. Pick signals from the catalog (or create new `Signal` instances in catalog.py).
2. Build one or more receptors (e.g. `NeatReceptor(..., inputs=catalog.DUAL_CPPN_VISUAL_INPUTS, ...)` or a custom `Receptor` subclass).
3. Set `self.sensory_system = SensorySystem(receptors=(...), outputs=..., substitutions=...)` in your representation's `__init__`.
4. Delegate expression to receptors; keep evolution (create_random, mutate, crossover) on the representation.

After changing signal lists used by NEAT representations, run **`make generate`** to sync NEAT num_inputs/num_outputs and frontend config.

# Signals

Representation-agnostic vocabulary for inputs and outputs. Used by all representations (CPPN, NCA, CA). Terms like receptors and sensory system are evo-algo style, not strict biology.

**Layout:** `sensory_system.py` (Signal, Output, SensorySystem), `catalog.py` (concrete signals and presets), `registry.py` (export, parse_time_inputs). `Receptor` and `NeatReceptor` live in **representation/receptors.py**; representations use receptors for expression.

**Extending:** Add or change signals in catalog.py; wire them in your representation’s receptors and `SensorySystem`. After changing inputs/outputs for a NEAT representation, run **`make generate`** to sync NEAT config and frontend.

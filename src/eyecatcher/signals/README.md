# Signals

The signal system provides a **representation-agnostic** vocabulary for inputs and outputs. A signal is a named value at the boundary of a representation -- it flows into or out of a computation, regardless of whether the computation is a neural network, a cellular automaton, or something else entirely.

## Architecture

```
signals/
  spec.py      -- Signal, Output, DerivedInput, SignalSpec (the primitives)
  catalog.py   -- Concrete signal instances by category + convenience presets
  registry.py  -- Parameterized helpers (export_for_frontend, parse_time_inputs, etc.)
```

### Self-describing signals

Each `Signal` carries enough metadata that no downstream code needs to branch on its ID:

- **is_spatial** -- value comes from position (e.g. x, y, distance); no uniform.
- **is_constant** -- fixed value (e.g. bias); no uniform, no enable toggle.
- **is_derived** -- value from internal computation (e.g. time from time network); no external uniform.
- **category** -- one of `"spatial"`, `"temporal"`, `"interaction"`, `"structural"` for grouping and temporal detection.

Toggleable signals (those that get a value uniform and an enable toggle in the shader) are exactly those where `not is_spatial and not is_constant`. The GLSL compiler emits flat `u_{id}` and `uEnable_{id}` uniforms; the frontend uses a flat `{ signal_id: boolean }` state.

### SignalSpec

Every representation declares a `signal_spec: SignalSpec` that tells the rest of the system what it accepts and produces:

```python
@dataclass(frozen=True)
class SignalSpec:
    inputs: tuple[Signal, ...]        # what flows in
    outputs: tuple[Output, ...]       # what flows out
    derived_inputs: tuple[DerivedInput, ...] = ()  # computed from other inputs
    groups: dict[str, tuple[str, ...]] = {}        # optional UI grouping; else grouped by category
```

No network names at the spec level. Internal routing (e.g. which signals go to which network in a dual-CPPN) is the representation's private concern.

### Signal Catalog

`catalog.py` provides composable building blocks:

- **SPATIAL**: `x`, `y`, `distance`
- **TEMPORAL**: `raw_time`, `time`
- **INTERACTION**: `mouse_speed`, `mouse_dist`, `activity`, `mouse_x`, `mouse_y`
- **STRUCTURAL**: `bias`
- **Derived**: `DISTANCE` (from x, y)
- **Outputs**: `RGB_OUTPUTS`, `TIME_OUTPUT`
- **Presets**: `DUAL_CPPN_VISUAL_INPUTS`, `DUAL_CPPN_TIME_INPUTS`, `CA_INTERACTION_INPUTS`

### How representations use the catalog

**DualCPPN**: Declares all visual inputs as its spec. Internally routes subsets to its visual and time networks.

**SingleCPPN**: Same visual inputs as dual-CPPN (single network, no time network).

**Conway CA**: Declares `mouse_x`, `mouse_y` as interaction signals. Internal routing maps these to the toggleMask / onCellInteraction mechanism.

### Consumers

The following parts of the system read from `representation.signal_spec`:

- **GLSL compiler** -- generates uniforms and enables from spec inputs
- **Frontend codegen** -- exports per-representation signal config
- **Viewer controls** -- builds UI from spec groups
- **Fitness functions** -- introspects spec to decide whether temporal sampling applies
- **NEAT validation** -- validates config against internal routing signal lists
- **Debug / inspection panel** -- reads signal labels from the spec

## Extending for new representations

1. Pick signals from the catalog (or create new `Signal` instances).
2. Build a `SignalSpec` with your inputs, outputs, derived inputs, and UI groups.
3. Set `self.signal_spec = ...` in your representation's `__init__`.
4. Internal routing is your concern -- map spec inputs to your internal computation.

The GLSL compiler, frontend, fitness functions, and all other consumers automatically adapt to your declared spec.

After changing signal lists used by NEAT, run `scripts/generate_signal_config.py` to emit the JS config and validate alignment.

# Signals

The signal system provides a **representation-agnostic** vocabulary for inputs and outputs. A signal is a named value at the boundary of a representation — it flows into or out of a computation, regardless of whether the computation is a neural network, a cellular automaton, or something else entirely.

## Architecture

```
signals/
  spec.py      -- Signal, Output, DerivedInput, SignalSpec (primitives + socket-centric spec)
  socket.py    -- Socket (to_array, default_values, input_ids); representation-agnostic binding
  catalog.py   -- Concrete signal instances by category + convenience presets
  registry.py  -- Parameterized helpers (export_for_frontend, parse_time_inputs, etc.)
```

Representation-specific socket implementations live in **representation/sockets.py** (e.g. `NeatSocket`, `GridSocket`). Representations never touch raw signal lists for expression — they use sockets.

### Self-describing signals

Each `Signal` carries enough metadata that no downstream code needs to branch on its ID:

- **is_spatial** — value comes from position (e.g. x, y, distance); no uniform.
- **is_constant** — fixed value (e.g. bias); no uniform, no enable toggle.
- **is_derived** — value from internal computation (e.g. time from time network); no external uniform.
- **category** — one of `"spatial"`, `"temporal"`, `"interaction"`, `"structural"` for grouping and temporal detection.

Toggleable signals (those that get a value uniform and an enable toggle in the shader) are exactly those where `not is_spatial and not is_constant`. The GLSL compiler emits flat `u_{id}` and `uEnable_{id}` uniforms; the frontend uses a flat `{ signal_id: boolean }` state.

### SignalSpec (socket-centric)

Every representation declares a `signal_spec: SignalSpec` that describes what it accepts and produces. The spec is **socket-centric**: sockets bind signals to each input target (e.g. one NEAT network, one grid).

```python
@dataclass(frozen=True)
class SignalSpec:
    sockets: tuple[Socket, ...] = ()   # one per input target (e.g. visual, time, interaction)
    outputs: tuple[Output, ...] = ()   # representation-level outputs
    substitutions: dict[str, str] = {} # e.g. {"time": "timeFromNetwork"}

    # Computed from sockets (deduped union):
    # .inputs, .derived_inputs, .socket(name), .input_ids(), .has_signal(id), .has_category(cat)
```

- **inputs** and **derived_inputs** are derived from all sockets (no manual lists at spec level).
- **groups** are gone: UI grouping uses `Signal.category` only.
- Representations that use NEAT networks hold `NeatSocket` instances; those that use a grid hold a `GridSocket`. The representation delegates expression (query, stats, PDF, etc.) to sockets and owns evolution (population, mutate, crossover).

### Socket

A **Socket** binds a set of signals to one input target. Base class is representation-agnostic:

- `to_array(values)` — build ordered input array from id → value dict (with derived applied).
- `default_values()` — id → default for all inputs.
- `input_ids()` — ordered list of input ids.

Subclasses add target-specific behaviour:

- **NeatSocket** (in `representation/sockets.py`): `config_path`, `query(genome, values)`, `glsl_input_map()`, `network_stats()`, `extract_network_data()`, `render_network_pdf()`.
- **GridSocket**: `grid_size`, `map_to_cell(values)` for e.g. CA interaction (mouse_x, mouse_y → cell).

### Signal catalog

`catalog.py` provides composable building blocks:

- **SPATIAL**: `x`, `y`, `distance`
- **TEMPORAL**: `raw_time`, `time`
- **INTERACTION**: `mouse_speed`, `mouse_dist`, `activity`, `mouse_x`, `mouse_y`
- **STRUCTURAL**: `bias`
- **Derived**: `DISTANCE` (from x, y)
- **Outputs**: `RGB_OUTPUTS`, `TIME_OUTPUT`
- **Presets**: `DUAL_CPPN_VISUAL_INPUTS`, `DUAL_CPPN_TIME_INPUTS`, `CA_INTERACTION_INPUTS`

Representations build sockets from these presets; the spec is then `SignalSpec(sockets=(...), outputs=..., substitutions=...)`.

### How representations use sockets

- **DualCPPN**: Two `NeatSocket`s (visual, time). Expression (query_rgb, get_compile_stats, get_network_data, render_network_pdf) delegates to the sockets; evolution (populations, mutate, crossover) stays on the representation.
- **SingleCPPN**: One `NeatSocket` (visual). Same split.
- **Conway CA**: One `GridSocket` (interaction) for mouse_x/mouse_y → cell; no NEAT.

### Consumers

The following read from `representation.signal_spec` or from sockets:

- **GLSL compiler** — `ShaderCompiler.from_spec(spec, color_mode)`; uniforms and enables from spec inputs.
- **Frontend codegen** — `export_for_frontend(spec)`; groups by category.
- **Viewer / API** — time output uses `spec.socket("time")` when present; default values from `socket.default_values()` or `get_default_signal_values(spec)`.
- **Fitness** — introspects `spec.inputs` for temporal category.
- **NEAT codegen** — `generate_signal_config.py` updates NEAT num_inputs/num_outputs from the representation’s socket counts (single source of truth) and validates.
- **Debug / inspection** — labels and structure from spec/sockets.

## Extending for new representations

1. Pick signals from the catalog (or create new `Signal` instances).
2. Build one or more sockets (e.g. `NeatSocket(..., inputs=catalog.DUAL_CPPN_VISUAL_INPUTS, ...)` or a custom `Socket` subclass).
3. Set `self.signal_spec = SignalSpec(sockets=(...), outputs=..., substitutions=...)` in your representation's `__init__`.
4. Delegate expression to sockets; keep evolution (create_random, mutate, crossover, population) on the representation.

After changing signal lists used by NEAT representations, run `make generate` (or `make generate-signals`): the script updates NEAT config num_inputs/num_outputs from the representation and emits the frontend signal list.

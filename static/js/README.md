# Frontend structure and JavaScript layout

**Entry points**

- `interactive_viewer.html` – main app (interactive evolution, population grid, evolve/save).
- `genealogy_viewer.html` – genealogy tree (load/save/export populations).

**Terminology:** The evolvable model type (e.g. dual_cppn, single_cppn, ca) is called **representation** everywhere: config ([config/experiments.json](../../config/experiments.json) key `"representation"`), API (`representation_id`), and this folder (`representation/`).

**JavaScript is grouped to mirror the backend** so you can find frontend counterparts of backend packages.

| Folder | Purpose | Backend counterpart |
|--------|---------|----------------------|
| **representation/** | Substrates, registry, config, pattern rendering (WebGL). | `representation/`, `glsl/` |
| **evolution/** | Evolution config, coordinator, viewer controls (signals, zoom). | `evolution/`, `signals/` |
| **community/** | Community browse, submit, admin UI. | `web/community_routes` |
| **genealogy/** | Genealogy viewer, export, thumbnails, sync. | `data/`, `web/genealogy_routes` |
| **inspection/** | Network visualizer, weight sliders, CPPN evaluator. | `inspection/` |
| **app/** | Application shell — state, grid, animation loop, toolbar, population UI. | — |
| **lib/** | API client, utils, toast, storage, debug. | `web/` (API) |

Script load order in the HTML: lib → evolution (config) → community → representation → evolution (viewer) → inspection / app (app loads last and wires everything).

---

## representation/ — Representations and rendering

**Edit when you change representation types or how patterns are drawn.**

Display is driven by **phenotype** (from the backend, per representation) and **substrates** (frontend framework). The registry builds a facade per representation from `RepresentationConfig` and the substrate chosen by `phenotype.substrate`. Researchers do not write JavaScript for standard substrates.

- **Substrate contract:** `substrate.js` — base class with six methods: `createDisplayElement`, `setup`, `teardown`, `buildParams`, `render`, `handleInteraction`. Only `createDisplayElement` and `render` are required; others have no-op defaults.
- `substrate_registry.js` — Routes `phenotype.substrate` (e.g. `"shader"`, `"grid"`, `"image"`) to a substrate instance. Unknown names fall back to ImageSubstrate.
- `shader_substrate.js` — Stateless GLSL: canvas, compile shader from pattern, fullscreen quad. Used by dual_cppn, single_cppn.
- `grid_substrate.js` — FBO ping-pong: step shader, display shader, toggle interaction from phenotype. Used by ca.
- `image_substrate.js` — Static image fallback (e.g. from backend `render_to_image()`). Used when no other substrate fits.
- `registry.js` — Bootstraps from RepresentationConfig; creates facades that delegate to substrate + phenotype. Resolve, getDisplayData, getAdapter.
- `config.generated.js` — Generated from Python representation export (do not edit).
- `webgl_utils.js` — WebGL 2 context, shader compile, fullscreen quad setup, FBO helpers. Rendering pipeline: registry `renderFrameWithSignals()` and adapter `buildParams` / `render`.

### Three substrates (no custom JS for standard cases)

1. **ShaderSubstrate** (`substrate="shader"`) — Backend compiles genome to a fragment shader. Frontend sets params per frame and draws a fullscreen quad. No state between frames. Set `phenotype = Phenotype(substrate="shader", meta_template="...")` in Python; run `make generate`. Example: dual_cppn, single_cppn.

2. **GridSubstrate** (`substrate="grid"`) — Backend provides step and display shaders (and optional toggle shader). Frontend maintains FBO state, runs step shader per tick, displays result. Set `phenotype = Phenotype(substrate="grid", grid_size=64, step_shader=..., display_shader=..., ...)` in Python. Example: ca. Future NCA would use this too.

3. **ImageSubstrate** (`substrate="image"` or unknown) — Backend evaluates and returns an image. Frontend displays it in an `<img>` tag. Set `phenotype = Phenotype(substrate="image")` and implement `render_to_image()` in Python. Example: trivial (or any representation that does not override phenotype).

### Adding a new substrate (new medium only)

Only if you need a new *medium* (e.g. audio): add a JS class extending `Substrate`, implement the six-method contract, and `registerSubstrate("audio", new AudioSubstrate())` in `substrate_registry.js`. Add the script to `REPRESENTATION_SCRIPTS` in `generate_representation_includes.py` and run `make generate`.

---

## evolution/ — Config and coordination

**Edit when you change evolution config, evolve flow, or signal/zoom UI.**

- `config.js` — Population size, signal toggles, representation id (representationId in JS), mergeFromServer (align with backend).
- `config_signals.generated.js` — Generated from Python signal registry (do not edit).
- `config_defaults.generated.js` — Generated from evolution_defaults.json (do not edit).
- `coordinator.js` — Parent selection, evolve API call.
- `viewer_controls.js` — Zoom and CPPN signal checkboxes (time/visual inputs).

---

## community/ — Community feature

**Edit when you change community browse, submit, or admin.**

- `index.js` — CommunityUI entry; share, browse, admin modals.
- `browse.js` — Fetch display data, build list entries, render previews.
- `submit.js` — Submit modal and form.
- `admin.js` — Admin modal, pending list, approve/reject.

---

## genealogy/ — Genealogy feature

**Edit when you change genealogy tree, export, or sync.**

- `viewer.js` — Genealogy tree page logic (load stats, branches, tree, load population).
- `export.js` — Export modal and download.
- `physics.js` — Physics sliders for tree layout.
- `network_config.js` — Network options for tree.
- `thumbnails.js` — Population thumbnails in tree.
- `sync.js` — Branch counter, sessionStorage, save-to-genealogy API (used by main app).

---

## inspection/ — Network and genome inspection

**Edit when you change network visualization or weight sliders.**

- `network_visualizer.js` — CPPN network sidebar (POST /api/network).
- `network_weight_sliders.js` — Weight sliders (POST /api/adjust-weight).
- `cppn_evaluator.js` — Client-side CPPN evaluator (not loaded in HTML; used by codegen for activation validation).

---

## app/ — Application shell

**Edit when you change app structure or main flow.**

- `app.js` — Entry point: wires DOM, inits modules, passes actions to features.
- `population_state.js` — Single source of truth for population, genomes, genealogy context.
- `grid_renderer.js` — Build and clear the pattern grid DOM.
- `fullscreen_modal.js` — Fullscreen pattern view.
- `animation_loop.js` — Time mode, mouse tracking, per-frame pattern render.
- `pattern_actions.js` — Save, click, unclick handlers.
- `app_event_bindings.js` — Global event bindings.
- `app_genealogy_loader.js` — Genealogy load from localStorage.
- `population_ui.js` — Start fresh, load/save population, import from file.
- `toolbar_ui.js` — Toolbar dropdowns and controls.

---

## lib/ — Shared infrastructure

**Only touch when fixing bugs or adding app-wide support.**

- `api_client.js` — Fetch for compile, evolve, save, random, genealogy, config.
- `utils.js` — Formatting, storage helpers, showLoading.
- `toast.js` — Notifications and download trigger.
- `storage.js` — IndexedDB wrapper for saved populations.
- `debug.js` — Debug overlay (optional).

API request/response bodies use **snake_case** (e.g. `representation_id`) to match the backend; internal JS uses **camelCase** (e.g. `representationId`).

---

## Rendering architecture

Patterns are rendered by **substrates** driven by **phenotype** and **environment signals**. The animation loop gets signal values and calls the registry facade, which delegates to the substrate.

### Pipeline overview

```
SignalSource.getValues(canvas)   →  signal values  { raw_time, mouse_speed, ... }
      ↓
facade.buildParams(signals)       →  params (substrate-specific, e.g. uniforms)
      ↓
substrate.render(state, params, signalState)
      ↓
gl.uniform1f / gl.drawArrays      →  pixels on canvas
```

Each pattern card has its own display element (canvas or img). The animation loop (`app/animation_loop.js`) calls `renderWithSignals()` once per pattern per frame, which gets signal values, calls `buildParams()`, then `render()` on the facade (which delegates to the substrate).

### Substrate lifecycle

1. **createDisplayElement** — Substrate creates the DOM element (canvas or img) and optional state. The registry then calls `substrate.setup(state, phenotype)` if present.
2. **preparePatternData** — Facade copies pattern metadata onto patternData (e.g. grid, patternId).
3. **Render loop** — Every frame, the animation loop gets signal values, calls `facade.buildParams(signalValues, context)`, then `facade.render(patternData, params, signalState)`.
4. **Teardown** — WebGL/resources are released when the canvas is removed from the DOM; substrates may implement `teardown(state)` for explicit cleanup.

### What the renderer supports today

| Capability                    | Supported | Notes |
|-------------------------------|-----------|-------|
| Fragment shaders (stateless)  | Yes       | ShaderSubstrate: fullscreen quad, params from signals |
| Scalar float uniforms         | Yes       | Via signal system + `substrate.buildParams()` |
| Integer uniforms              | Yes       | Set in substrate `render()` (e.g. GridSubstrate) |
| Custom vertex shader          | No        | Shared fullscreen quad |
| Framebuffer objects (FBOs)    | Yes       | GridSubstrate uses `WebGLUtils.createFBO` / `swapFBOs` |
| Texture uniforms (sampler2D)  | Partial   | FBO textures in grid substrate |
| Multi-pass rendering          | Partial   | GridSubstrate step then display |
| Per-pixel click interaction   | Yes       | GridSubstrate handles toggle/draw from phenotype.interactions |

### Extension points

- **New substrate:** Implement the six-method contract in a new file, register in `substrate_registry.js`, add to script list, run `make generate`.
- **Pixel-level interaction:** Substrates implement `handleInteraction(state, x, y, type)`; the registry wires it when `phenotype.interactions` includes e.g. `"toggle"` or `"draw"`.

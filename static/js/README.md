# Frontend structure and JavaScript layout

**Entry points**

- `interactive_viewer.html` – main app (interactive evolution, population grid, evolve/save).
- `genealogy_viewer.html` – genealogy tree (load/save/export populations).

**Terminology:** The backend uses the term **representation** for the evolvable model type (e.g. dual_cppn, single_cppn, ca). In the frontend, folder names and many variables still use **substrate** (legacy). API responses use `representation_id`; JS may refer to "substrate" in adapters and config. Treat them as the same concept.

**JavaScript is grouped to mirror the backend** so you can find frontend counterparts of backend packages.

| Folder | Purpose | Backend counterpart |
|--------|---------|----------------------|
| **substrate/** | Representation adapters, registry, config, pattern rendering (WebGL). | `representation/`, `glsl/` |
| **evolution/** | Evolution config, coordinator, viewer controls (signals, zoom). | `evolution/`, `signals/` |
| **community/** | Community browse, submit, admin UI. | `web/community_routes` |
| **genealogy/** | Genealogy viewer, export, thumbnails, sync. | `data/`, `web/genealogy_routes` |
| **inspection/** | Network visualizer, weight sliders, CPPN evaluator. | `inspection/` |
| **app/** | Application shell — state, grid, animation loop, toolbar, population UI. | — |
| **lib/** | API client, utils, toast, storage, debug. | `web/` (API) |

Script load order in the HTML: lib → evolution (config) → community → substrate → evolution (viewer) → inspection / app (app loads last and wires everything).

---

## substrate/ — Representations and rendering

**Edit when you change representation types or how patterns are drawn.** (Folder name is legacy; backend concept is "representation".)

- `registry.js` — Adapter registry (SubstrateAdapters), resolve, getDisplayData, registers from SubstrateConfig.
- `cppn_adapter.js` — Shared CPPN adapter (dual_cppn, single_cppn); createCppnAdapter(spec).
- `ca.js` — CA (Conway GOL) adapter; stateful grid, FBO ping-pong.
- `config.generated.js` — Generated from Python substrate export (do not edit).
- `pattern_renderer.js` — WebGL 2 setup, shader compile, renderWithSignals, createPatternCard, FBO helpers.

---

## evolution/ — Config and coordination

**Edit when you change evolution config, evolve flow, or signal/zoom UI.**

- `config.js` — Population size, signal toggles, representation id (substrateId in JS), mergeFromServer (align with backend).
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

API request/response bodies use **snake_case** (e.g. `substrate_id`, `output_type`) to match the backend; internal JS uses **camelCase** (e.g. `substrateId`, `outputType`).

---

## Rendering architecture

This section describes how patterns get from data to pixels. Read this before writing a custom substrate adapter.

### Pipeline overview

```
SignalSource.getValues(canvas)   →  signal values  { raw_time, mouse_speed, ... }
      ↓
adapter.buildUniforms(signals)   →  uniform dict   { u_raw_time: 0.5, ... }
      ↓
adapter.render(patternData, uniforms, signalState)
      ↓
gl.uniform1f / gl.drawArrays    →  pixels on canvas
```

Each pattern card has its own `<canvas>` with its own WebGL 2 context. The animation loop (`app/animation_loop.js`) calls `renderWithSignals()` once per pattern per frame via `requestAnimationFrame`.

### Pattern lifecycle

1. **Setup** — `PatternRenderer.setupPattern(canvas, shaderCode)` creates a WebGL 2 context, compiles the vertex + fragment shader into a program, and creates a fullscreen-quad position buffer. Returns `{ gl, program, positionBuffer }`.
2. **Prepare** — `adapter.preparePatternData(patternData, pattern)` stores substrate-specific fields (e.g. `patternData.grid` for CA).
3. **Render loop** — Every frame, the animation loop iterates all patterns and calls `renderWithSignals(patternData, patternRenderer, signalState, canvas)`. This: gets signal values from the active `SignalSource`, builds uniforms via `adapter.buildUniforms()`, and calls `adapter.render()`.
4. **Teardown** — Currently none; WebGL resources are released when the canvas is removed from the DOM.

### Adapter lifecycle hooks (optional)

Adapters can implement optional lifecycle methods for stateful rendering:

- `onSetup(patternData, gl)` — Called once after `setupPattern`. Use for FBO/texture creation.
- `onBeforeRender(patternData, context)` — Called before each frame's `render()`. Context includes `{ gl, canvas, gridPosition, neighbors, frameCount, deltaTime }`.
- `render(patternData, uniformValues, signalState)` — **Required.** Main draw call.
- `onAfterRender(patternData, context)` — Called after each frame's `render()`. Use for FBO swap, edge-state export.
- `onTeardown(patternData, gl)` — Called when the pattern is removed. Use for FBO/texture cleanup.

### What the renderer supports today

| Capability                    | Supported | Notes |
|-------------------------------|-----------|-------|
| Fragment shaders (stateless)  | Yes       | Each frame draws from scratch using uniforms |
| Scalar float uniforms         | Yes       | Via signal system + `adapter.buildUniforms()` |
| Integer uniforms              | Yes       | Set directly in `adapter.render()` (see CA adapter) |
| Custom vertex shader          | No        | Hard-coded fullscreen quad in `pattern_renderer.js` |
| Framebuffer objects (FBOs)    | Yes       | Via `PatternRenderer.createFBO()` / `swapFBOs()` helpers |
| Texture uniforms (sampler2D)  | Partial   | FBO textures can be bound; no general texture upload yet |
| Multi-pass rendering          | Partial   | Adapters can do multiple draw calls in `render()` using FBOs |
| Cross-pattern communication   | Yes       | Via `GridTopology` (neighbor lookup) and adapter lifecycle hooks |
| Per-pixel click interaction   | Yes       | Via `PatternRenderer.getClickCoordinates(event, canvas)` |

### Extension points

- **New uniform types:** Set any uniform in your `adapter.render()` method (you have full access to `gl` and `program`).
- **Stateful rendering (FBOs):** Use `PatternRenderer.createFBO(gl, width, height)` in `adapter.onSetup()` and ping-pong between FBOs in `render()`.
- **Pixel-level interaction:** Use `PatternRenderer.getClickCoordinates(event, canvas)` to get normalized (0–1) coordinates from a click event. Wire the result into your adapter's state (e.g. a kill-mask texture).
- **Neighbor communication:** Use `GridTopology.getNeighbors(patternId)` and `GridTopology.getGridPosition(patternId)` to find adjacent patterns. Exchange state via `adapter.onAfterRender()` (write edge state) and `adapter.onBeforeRender()` (read neighbor edge state).

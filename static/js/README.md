# Frontend JavaScript layout

The JS code is grouped into four folders so you can quickly see **what to edit** vs **what to leave alone**.

---

## **evolution/** — Where the experiment lives

**Edit this when you change how evolution, signals, or rendering work.**

- `evolution_config.js` — Population size, signal toggles, canvas limits (align with backend).
- `evolution_coordinator.js` — Parent selection, evolve API call, population size from UI.
- `pattern_renderer.js` — WebGL: compile and draw dual-CPPN fragment shaders.
- `viewer_controls.js` — Zoom and CPPN signal checkboxes (time/visual inputs).
- `cppn_evaluator.js` — CPPN evaluation helpers if used.

Signals, evolution behavior, and how patterns are drawn are defined here. This is the code that defines your experiment.

---

## **app/** — Application shell

**Edit this when you change how the app is wired (state, coordination, or main flow).**

- `app.js` — Entry point: wires DOM, inits modules, passes actions to features.
- `population_state.js` — Single source of truth for population, genomes, genealogy context.
- `grid_renderer.js` — Build and clear the pattern grid DOM.
- `fullscreen_modal.js` — Fullscreen pattern view.
- `genealogy_sync.js` — Branch counter, sessionStorage, save-to-genealogy API.
- `animation_loop.js` — Time mode, mouse tracking, per-frame pattern render.

You’ll rarely need to change these unless you’re changing app structure or adding new flows.

---

## **lib/** — Shared / infrastructure

**Only touch when fixing bugs or adding cross‑cutting support.**

- `api_client.js` — Fetch for compile, evolve, save, random, genealogy.
- `utils.js` — Formatting, storage helpers, showLoading.
- `toast.js` — Notifications and download trigger.
- `storage.js` — IndexedDB wrapper for saved populations.
- `debug.js` — Debug overlay (optional).

No evolution or experiment logic; just support used by the rest of the app.

---

## **features/** — Optional features

**Edit when you care about that specific feature.**

- `population_ui.js` — Start fresh, load/save population, import from file.
- `community.js` — Share to community, browse, admin.
- `network_visualizer.js` — CPPN network sidebar, weight sliders.
- `toolbar_ui.js` — Toolbar dropdowns and controls.
- `genealogy_viewer.js` — Genealogy tree page (loads in its own HTML).

Each file is a self-contained feature; you can ignore the ones you don’t use.

---

## Summary

| Folder      | When you look here |
|------------|---------------------|
| **evolution/** | Changing signals, evolution, rendering, or viewer behavior. |
| **app/**      | Changing how the app is structured or how state/flow works. |
| **lib/**      | Fixing API, utils, or adding app-wide support. |
| **features/**  | Changing a specific feature (community, genealogy, network viz, etc.). |

Script load order in the HTML matches this: lib → evolution → features → app (so the shell loads last and can wire everything).

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

Each pattern card has its own `<canvas>` with its own WebGL 2 context. The animation loop (`animation_loop.js`) calls `renderWithSignals()` once per pattern per frame via `requestAnimationFrame`.

### Pattern lifecycle

1. **Setup** — `PatternRenderer.setupPattern(canvas, shaderCode)` creates a WebGL 2 context, compiles the vertex + fragment shader into a program, and creates a fullscreen-quad position buffer. Returns `{ gl, program, positionBuffer }`.
2. **Prepare** — `adapter.preparePatternData(patternData, pattern)` stores substrate-specific fields (e.g. `patternData.caRule` for CA).
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

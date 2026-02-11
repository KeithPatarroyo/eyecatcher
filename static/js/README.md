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

# Frontend structure

**Entry points**

- `interactive_viewer.html` – main app (interactive evolution, population grid, breed/save).
- `genealogy_viewer.html` – genealogy tree (load/save/export populations).

**Scripts (static/js/modules/)**

- `app.js` – wires DOM and inits modules; load last.
- `pattern_renderer.js` – WebGL, dual-CPPN fragment shaders.
- `viewer_controls.js` – zoom and signal toggles.
- `evolution_config.js` – frontend constants aligned with backend.
- `api_client.js` – fetch for compile, breed, save, random, genealogy.
- `app_core.js` – state, grid, breed/save logic (no DOM).
- `population_ui.js`, `community.js` – population and community UI.
- `network_visualizer.js` – CPPN sidebar, vis.js, weight sliders.
- `animation_loop.js` – mouse/time, per-frame render.
- `toolbar_ui.js`, `debug.js`, `storage.js`, `toast.js`, `utils.js`, `cppn_evaluator.js`.
- `genealogy_viewer.js` – tree UI; uses vis.js, PatternRenderer for thumbnails.

Script load order is defined in each HTML entry point.

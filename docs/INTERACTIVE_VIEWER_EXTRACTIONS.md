# Interactive viewer: further extractions for easier merges

**Goal:** Shrink `interactive_viewer.html` and move change-prone blocks into separate files so future merges (with main, sketch, visualization-genome, cppn-toggle-buttons, dual-cppn-real-time) conflict in smaller, focused files instead of one big HTML.

**Current state:** ~1676 lines (inline CSS + HTML + inline JS). Population/community logic already lives in `population_ui.js` and `community.js`.

---

## 1. Extract inline CSS → `viewer.css` (recommended first)

**What:** Move the entire `<style>…</style>` block (lines ~8–666, ~658 lines) into a new file `viewer.css` and link it from the HTML.

**Why:**
- **Largest single reduction** in HTML size (~650 lines).
- **Zero behavior change**; only presentation.
- Other branches often add or tweak styles (time controls, buttons, modals, grid). Those changes would then conflict in `viewer.css` instead of in the middle of the HTML.
- Merge resolution becomes “fix CSS” in one file instead of resolving inside a 1600-line file.

**Risk:** Very low. Load order: existing `debug.css` and `community.css` stay; add `<link rel="stylesheet" href="viewer.css">` and remove the inline `<style>` block.

---

## 2. Extract WebGL / pattern renderer → `pattern_renderer.js` (recommended second)

**What:** Move into a small module:
- `createWebGLContext`, `compileShader`, `createProgram`
- `vertexShaderSource` (the vertex shader string)
- `setupPattern(canvas, shaderCode)` → returns pattern data
- `renderPattern(patternData, time, mouseSpd, mouseDist, inact, signalState)` → needs `signalState` passed in so the module stays stateless

Expose e.g. `window.PatternRenderer = { setupPattern, renderPattern }`. The HTML (and `community.js`, which already receives `setupPattern`/`renderPattern` from the page) would call these instead of defining them inline.

**Why:**
- Removes ~100 lines from the HTML (WebGL setup + vertex shader + setup/render).
- Branches that change shader inputs, uniforms, or rendering (e.g. dual-cppn-real-time, cppn-toggle-buttons) would often touch this block; having it in `pattern_renderer.js` confines those conflicts to one file.
- Keeps a single place for “how we compile and draw a pattern,” which is good for maintainability.

**Risk:** Low. Only dependency is `signalState` for `renderPattern`; pass it in as an argument so the module doesn’t depend on the rest of the page.

**Note:** `community.js` is already initialized with `setupPattern` and `renderPattern` from the page. After extraction, the HTML would pass `PatternRenderer.setupPattern` and `PatternRenderer.renderPattern` (with a small wrapper that supplies `signalState` if needed).

---

## 3. Optional: Signal controls init → `signal_controls.js`

**What:** Move `initSignalControls()` and `initTimeModeControls()` into a small module that receives:
- `signalState` (object, by reference so checkboxes can update it)
- References to zoom controls and time-mode radios

**Why:** Slightly shrinks the HTML and isolates “wire up signal checkboxes and time mode” in one place. When main or other branches change time mode or signal toggles, conflicts are in `signal_controls.js` instead of the big HTML.

**Risk:** Low. The only subtlety is that `signalState` and zoom state (`patternZoom`, `applyZoom`) are used in `animate()` and `renderPattern`, so they stay in the HTML; only the *initialization* of the checkboxes and zoom buttons moves.

**Benefit:** Smaller than (1) and (2); do after CSS and pattern renderer if you want to go further.

---

## 4. Optional later: Grid / population loading

**What:** Move `showGridError`, `renderGridFromPopulation`, `loadPopulation`, `loadFromStatelessGenomes` into a module (e.g. `grid_controller.js`) that is inited with `API_URL`, `patterns`, `setupPattern`, `renderPattern`, and callbacks for “loading started/stopped.”

**Why:** These blocks are large and are the kind of thing that might be extended (e.g. different grid layouts, loading UIs). Isolating them would further reduce the size of the inline script.

**Risk:** Medium. Many dependencies (patterns Map, API_URL, setupPattern, CommunityUI.openSubmitCommunityModal, etc.). Do only if you want to push the HTML down to a thin “wire-up and config” layer.

---

## Summary

| Extraction            | Lines out of HTML (approx.) | Merge benefit                          | Risk   |
|----------------------|-----------------------------|----------------------------------------|--------|
| 1. CSS → viewer.css  | ~650                        | Style conflicts in one file            | Very low |
| 2. WebGL → pattern_renderer.js | ~100                | Shader/rendering conflicts in one file| Low   |
| 3. Signal controls  | ~50                         | Time/signal init in one file           | Low   |
| 4. Grid / loading    | ~150+                      | Grid/load logic in one file            | Medium |

**Suggested order:** Do (1) first, then (2). That alone cuts the HTML by ~750 lines and keeps future style and rendering conflicts out of the monolithic file without hurting merges.

---

## Done

- **1. CSS → viewer.css** – Implemented. Inline styles moved to `viewer.css`.
- **2. WebGL → pattern_renderer.js** – Implemented. `PatternRenderer.setupPattern` and `PatternRenderer.renderPattern(patternData, time, mouseSpd, mouseDist, inact, signalState)` live in `pattern_renderer.js`; the HTML keeps thin wrappers that pass `signalState` into `renderPattern`. `CommunityUI.init` still receives the same `setupPattern`/`renderPattern` from the page (the wrappers).

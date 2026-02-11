# Frontend structure

**Entry points**

- `interactive_viewer.html` – main app (interactive evolution, population grid, evolve/save).
- `genealogy_viewer.html` – genealogy tree (load/save/export populations).

**JavaScript is grouped by role** so you can see what to edit vs what to leave alone. See **[js/README.md](js/README.md)** for the full guide.

| Folder | Purpose |
|--------|---------|
| **js/evolution/** | Where the experiment lives — signals, evolution, pattern rendering, viewer controls. Edit when you change evolution or viewer behavior. |
| **js/app/** | Application shell — app.js, state, grid, fullscreen, genealogy sync, animation loop. Edit when you change app structure or flow. |
| **js/lib/** | Shared infrastructure — API client, utils, toast, storage, debug. Only touch for bugs or app-wide support. |
| **js/features/** | Optional features — population UI, community, network visualizer, toolbar, genealogy viewer. Edit when you care about that feature. |

Script load order in the HTML: lib → evolution → features → app (shell loads last and wires everything).

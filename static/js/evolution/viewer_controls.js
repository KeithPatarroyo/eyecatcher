// viewer_controls.js (replace whole file)
(() => {
    "use strict";

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.1;

    const el = (id) => document.getElementById(id);

    const renderSignalControls = (signalGroups) => {
        const container = el("signal-controls");
        if (!container) return;

        container.innerHTML = "";
        if (!signalGroups?.length) return;

        const frag = document.createDocumentFragment();

        signalGroups.forEach((groupDef, idx) => {
            const group = document.createElement("div");
            group.className = "signal-group";

            const title = document.createElement("div");
            title.className = "signal-group-title";
            title.textContent = groupDef.label ?? "";
            group.appendChild(title);

            const wrap = document.createElement("div");
            wrap.className = "signal-checkboxes";

            (groupDef.signals ?? []).forEach((s) => {
                const row = document.createElement("div");
                row.className = `signal-checkbox${s.derived ? " signal-derived" : ""}`;

                const input = document.createElement("input");
                input.type = "checkbox";
                input.id = `signal-${s.id}`;
                input.dataset.signalId = s.id;

                const label = document.createElement("label");
                label.htmlFor = input.id;

                if (s.derived) {
                    label.appendChild(document.createTextNode(`${s.label} `));
                    const hint = document.createElement("span");
                    hint.className = "signal-hint";
                    hint.textContent = "(from Time Signal)";
                    label.appendChild(hint);
                } else {
                    label.textContent = s.label ?? s.id;
                }

                row.append(input, label);
                wrap.appendChild(row);
            });

            group.appendChild(wrap);
            frag.appendChild(group);

            if (idx + 1 < signalGroups.length) {
                const flow = document.createElement("div");
                flow.className = "signal-flow";
                flow.textContent = "→";
                frag.appendChild(flow);
            }
        });

        container.appendChild(frag);
    };

    class ViewerControls {
        patternZoom = 1.0;
        signalState = {};
        _signalsBound = false;

        applyZoom() {
            document.documentElement.style.setProperty(
                "--pattern-zoom",
                String(this.patternZoom)
            );
            const label = el("zoom-label");
            if (label) label.textContent = `${Math.round(this.patternZoom * 100)}%`;
        }

        _syncCheckboxes(representationId) {
            const cfg = window.EvolutionConfig;
            const toggles = cfg?.getToggleableSignals?.(representationId) ?? [];
            const defaults = cfg?.getDefaultSignalState?.(representationId) ?? {};

            for (const s of toggles) {
                if (this.signalState[s.id] === undefined)
                    this.signalState[s.id] = defaults[s.id] !== false;
                const checkbox = el(`signal-${s.id}`);
                if (checkbox) checkbox.checked = !!this.signalState[s.id];
            }
        }

        updateForRepresentation(representationId) {
            const container = el("signal-controls");
            if (!container) return;

            const representation =
                window.RepresentationRegistry?.get?.(representationId);
            const show =
                representation === null
                    ? true
                    : representation?.hasSignalControls !== false;
            container.style.display = show ? "" : "none";

            const cfg = window.EvolutionConfig;
            const signalGroups = cfg?.getSignalGroups?.(representationId) ?? [];
            renderSignalControls(signalGroups);
            this._syncCheckboxes(representationId);

            const gridHint = el("instructions-grid-hint");
            if (gridHint) {
                const sub = representation?.phenotype?.substrate;
                const isGrid = sub?.type === "grid" || sub === "grid";
                gridHint.hidden = !isGrid;
            }
        }

        init() {
            const cfg = window.EvolutionConfig;
            const representationId = cfg?.getCurrentRepresentationId?.() ?? "";

            // One delegated listener instead of N listeners.
            if (!this._signalsBound) {
                const container = el("signal-controls");
                if (container) {
                    container.addEventListener("change", (e) => {
                        const input = e.target;
                        const signalId = input?.dataset?.signalId;
                        if (!signalId) return;
                        this.signalState[signalId] = !!input.checked;
                    });
                }
                this._signalsBound = true;
            }

            const Utils = window.Utils;
            const zoomIn = el("zoom-in");
            const zoomOut = el("zoom-out");

            if (zoomIn && Utils?.onRoleButtonKeydown) {
                Utils.onRoleButtonKeydown(zoomIn, () => {
                    this.patternZoom = Math.min(ZOOM_MAX, this.patternZoom + ZOOM_STEP);
                    this.applyZoom();
                });
            }

            if (zoomOut && Utils?.onRoleButtonKeydown) {
                Utils.onRoleButtonKeydown(zoomOut, () => {
                    this.patternZoom = Math.max(ZOOM_MIN, this.patternZoom - ZOOM_STEP);
                    this.applyZoom();
                });
            }

            this.applyZoom();
            this.updateForRepresentation(representationId);
        }
    }

    window.ViewerControls = new ViewerControls();
})();

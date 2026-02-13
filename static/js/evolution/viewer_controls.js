/**
 * Pattern grid zoom and signal checkbox state for substrate input toggles.
 * Exposes: ViewerControls.patternZoom, ViewerControls.signalState, ViewerControls.applyZoom(), ViewerControls.init()
 */
(function () {
    "use strict";

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.1;

    function populateSignalControls(signalGroups) {
        const container = document.getElementById("signal-controls");
        if (!container || !signalGroups || !signalGroups.length) return;
        container.innerHTML = "";
        for (var i = 0; i < signalGroups.length; i++) {
            var groupDef = signalGroups[i];
            var group = document.createElement("div");
            group.className = "signal-group";
            var titleEl = document.createElement("div");
            titleEl.className = "signal-group-title";
            titleEl.textContent = groupDef.label;
            group.appendChild(titleEl);
            var checkboxesWrap = document.createElement("div");
            checkboxesWrap.className = "signal-checkboxes";
            (groupDef.signals || []).forEach(function (s) {
                var wrap = document.createElement("div");
                wrap.className =
                    "signal-checkbox" + (s.derived ? " signal-derived" : "");
                var input = document.createElement("input");
                input.type = "checkbox";
                input.id = "signal-" + s.id;
                input.checked = true;
                var label = document.createElement("label");
                label.htmlFor = input.id;
                if (s.derived) {
                    label.appendChild(document.createTextNode(s.label + " "));
                    var hintDerived = document.createElement("span");
                    hintDerived.className = "signal-hint";
                    hintDerived.textContent = "(from Time Signal)";
                    label.appendChild(hintDerived);
                } else {
                    label.textContent = s.label;
                }
                wrap.appendChild(input);
                wrap.appendChild(label);
                checkboxesWrap.appendChild(wrap);
            });
            group.appendChild(checkboxesWrap);
            container.appendChild(group);
            if (i + 1 < signalGroups.length) {
                var flow = document.createElement("div");
                flow.className = "signal-flow";
                flow.textContent = "→";
                container.appendChild(flow);
            }
        }
    }

    const ViewerControls = {
        patternZoom: 1.0,
        signalState: (function () {
            var config = window.EvolutionConfig;
            return config && config.getDefaultSignalState
                ? config.getDefaultSignalState()
                : {};
        })(),
        applyZoom: function () {
            document.documentElement.style.setProperty(
                "--pattern-zoom",
                String(this.patternZoom)
            );
            const label = document.getElementById("zoom-label");
            if (label) label.textContent = Math.round(this.patternZoom * 100) + "%";
        },
        /**
         * Show or hide signal controls based on substrate adapter (e.g. hide for CA, single_cppn).
         * Call after load or addToGrid when substrateId changes.
         * @param {string|null} substrateId - current substrate id
         */
        updateForSubstrate: function (substrateId) {
            const container = document.getElementById("signal-controls");
            if (!container) return;
            const adapter = window.SubstrateAdapters.getAdapter(substrateId);
            const show = adapter === null ? true : adapter.hasSignalControls !== false;
            container.style.display = show ? "" : "none";
        },
        init: function () {
            const self = this;
            const config = window.EvolutionConfig;
            const signalGroups = config && config.SIGNAL_GROUPS;
            const toggleableSignals = config && config.TOGGLEABLE_SIGNALS;
            if (toggleableSignals && toggleableSignals.length) {
                toggleableSignals.forEach(function (s) {
                    if (self.signalState[s.id] === undefined) {
                        self.signalState[s.id] = true;
                    }
                });
            }
            if (signalGroups && signalGroups.length) {
                populateSignalControls(signalGroups);
                if (toggleableSignals) {
                    toggleableSignals.forEach(function (s) {
                        const checkbox = document.getElementById("signal-" + s.id);
                        if (checkbox) {
                            checkbox.addEventListener("change", function (e) {
                                self.signalState[s.id] = e.target.checked;
                            });
                        }
                    });
                }
            }
            const zoomIn = document.getElementById("zoom-in");
            const zoomOut = document.getElementById("zoom-out");
            if (zoomIn) {
                zoomIn.addEventListener("click", function () {
                    self.patternZoom = Math.min(ZOOM_MAX, self.patternZoom + ZOOM_STEP);
                    self.applyZoom();
                });
                zoomIn.addEventListener("keydown", function (e) {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        zoomIn.click();
                    }
                });
            }
            if (zoomOut) {
                zoomOut.addEventListener("click", function () {
                    self.patternZoom = Math.max(ZOOM_MIN, self.patternZoom - ZOOM_STEP);
                    self.applyZoom();
                });
                zoomOut.addEventListener("keydown", function (e) {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        zoomOut.click();
                    }
                });
            }
            this.applyZoom();
            const substrateId = window.PopulationState.getState().substrateId;
            this.updateForSubstrate(substrateId);
        },
    };

    window.ViewerControls = ViewerControls;
})();

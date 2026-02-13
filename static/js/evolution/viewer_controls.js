/**
 * Pattern grid zoom and CPPN signal checkbox state (viewer controls).
 * Exposes: ViewerControls.patternZoom, ViewerControls.signalState, ViewerControls.applyZoom(), ViewerControls.init()
 */
(function () {
    "use strict";

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.1;

    function titleForNetworkType(cppnType) {
        if (cppnType === "time") return "Time Signal Inputs";
        if (cppnType === "visual") return "Visual Inputs";
        return cppnType.charAt(0).toUpperCase() + cppnType.slice(1) + " Inputs";
    }

    function populateSignalControls(config) {
        const container = document.getElementById("signal-controls");
        if (!container || !config) return;
        container.innerHTML = "";
        const networkTypes = window.EvolutionConfig.NETWORK_TYPES || ["time", "visual"];
        networkTypes.forEach(function (cppnType) {
            const group = document.createElement("div");
            group.className = "signal-group";
            const titleEl = document.createElement("div");
            titleEl.className = "signal-group-title";
            titleEl.textContent = titleForNetworkType(cppnType);
            group.appendChild(titleEl);
            const checkboxesWrap = document.createElement("div");
            checkboxesWrap.className = "signal-checkboxes";
            config[cppnType].toggleableInputs.forEach(function (s) {
                const wrap = document.createElement("div");
                wrap.className =
                    "signal-checkbox" + (s.derived ? " signal-derived" : "");
                const input = document.createElement("input");
                input.type = "checkbox";
                input.id = cppnType + "-" + s.id;
                input.checked = true;
                const label = document.createElement("label");
                label.htmlFor = input.id;
                if (cppnType === "time" && s.id === "raw_time") {
                    label.appendChild(document.createTextNode(s.label + " "));
                    const hint = document.createElement("span");
                    hint.className = "signal-hint";
                    hint.textContent = "(from Time Mode above)";
                    label.appendChild(hint);
                } else if (s.derived) {
                    label.appendChild(document.createTextNode(s.label + " "));
                    const hint = document.createElement("span");
                    hint.className = "signal-hint";
                    hint.textContent = "(from Time Signal)";
                    label.appendChild(hint);
                } else {
                    label.textContent = s.label;
                }
                wrap.appendChild(input);
                wrap.appendChild(label);
                checkboxesWrap.appendChild(wrap);
            });
            group.appendChild(checkboxesWrap);
            container.appendChild(group);
            if (cppnType === "time") {
                const flow = document.createElement("div");
                flow.className = "signal-flow";
                flow.textContent = "→";
                container.appendChild(flow);
            }
        });
    }

    const ViewerControls = {
        patternZoom: 1.0,
        signalState: { time: {}, visual: {} },
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
            const config = window.EvolutionConfig.SIGNAL_TOGGLES;
            if (config) {
                populateSignalControls(config);
                (window.EvolutionConfig.NETWORK_TYPES || ["time", "visual"]).forEach(
                    function (cppnType) {
                        config[cppnType].toggleableInputs.forEach(function (s) {
                            self.signalState[cppnType][s.id] = true;
                            const checkbox = document.getElementById(
                                cppnType + "-" + s.id
                            );
                            if (checkbox) {
                                checkbox.addEventListener("change", function (e) {
                                    self.signalState[cppnType][s.id] = e.target.checked;
                                });
                            }
                        });
                    }
                );
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

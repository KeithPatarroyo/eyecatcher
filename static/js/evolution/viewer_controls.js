/**
 * Pattern grid zoom and signal checkbox state for substrate input toggles.
 * Exposes: ViewerControls.patternZoom, ViewerControls.signalState, ViewerControls.applyZoom(), ViewerControls.init()
 */
(function () {
    "use strict";

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.1;

    const NETWORK_TYPE_LABELS = {
        time: "Time Signal Inputs",
        visual: "Visual Network Inputs",
    };

    function titleForNetworkType(networkType) {
        return (
            NETWORK_TYPE_LABELS[networkType] ||
            networkType.charAt(0).toUpperCase() + networkType.slice(1) + " Inputs"
        );
    }

    function populateSignalControls(config) {
        const container = document.getElementById("signal-controls");
        if (!container || !config) return;
        container.innerHTML = "";
        const networkTypes = window.EvolutionConfig.NETWORK_TYPES || ["time", "visual"];
        for (var i = 0; i < networkTypes.length; i++) {
            var networkType = networkTypes[i];
            var group = document.createElement("div");
            group.className = "signal-group";
            var titleEl = document.createElement("div");
            titleEl.className = "signal-group-title";
            titleEl.textContent = titleForNetworkType(networkType);
            group.appendChild(titleEl);
            var checkboxesWrap = document.createElement("div");
            checkboxesWrap.className = "signal-checkboxes";
            config[networkType].toggleableInputs.forEach(function (s) {
                var wrap = document.createElement("div");
                wrap.className =
                    "signal-checkbox" + (s.derived ? " signal-derived" : "");
                var input = document.createElement("input");
                input.type = "checkbox";
                input.id = networkType + "-" + s.id;
                input.checked = true;
                var label = document.createElement("label");
                label.htmlFor = input.id;
                if (networkType === "time" && s.id === "raw_time") {
                    label.appendChild(document.createTextNode(s.label + " "));
                    var hintTime = document.createElement("span");
                    hintTime.className = "signal-hint";
                    hintTime.textContent = "(from Time Mode above)";
                    label.appendChild(hintTime);
                } else if (s.derived) {
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
            /* One separator between each pair of groups (N groups → N-1 gaps). */
            if (i + 1 < networkTypes.length) {
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
            var s = {};
            var types = window.EvolutionConfig && window.EvolutionConfig.NETWORK_TYPES;
            if (types && types.length) {
                types.forEach(function (t) {
                    s[t] = {};
                });
            }
            return s;
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
            const types =
                window.EvolutionConfig && window.EvolutionConfig.NETWORK_TYPES
                    ? window.EvolutionConfig.NETWORK_TYPES
                    : ["time", "visual"];
            types.forEach(function (t) {
                if (!self.signalState[t]) self.signalState[t] = {};
            });
            const config = window.EvolutionConfig.SIGNAL_TOGGLES;
            if (config) {
                populateSignalControls(config);
                types.forEach(function (networkType) {
                    if (config[networkType] && config[networkType].toggleableInputs) {
                        config[networkType].toggleableInputs.forEach(function (s) {
                            self.signalState[networkType][s.id] = true;
                            const checkbox = document.getElementById(
                                networkType + "-" + s.id
                            );
                            if (checkbox) {
                                checkbox.addEventListener("change", function (e) {
                                    self.signalState[networkType][s.id] =
                                        e.target.checked;
                                });
                            }
                        });
                    }
                });
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

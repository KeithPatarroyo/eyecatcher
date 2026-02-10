/**
 * Pattern grid zoom and CPPN signal checkbox state (viewer controls).
 * Exposes: ViewerControls.patternZoom, ViewerControls.signalState, ViewerControls.applyZoom(), ViewerControls.init()
 */
(function () {
    "use strict";

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.1;

    function populateSignalControls(config) {
        const container = document.getElementById("signal-controls");
        if (!container || !config) return;
        container.innerHTML = "";
        const titles = {
            time: "Time Signal CPPN Inputs",
            visual: "Visual CPPN Inputs",
        };
        ["time", "visual"].forEach(function (cppnType) {
            const group = document.createElement("div");
            group.className = "signal-group";
            const titleEl = document.createElement("div");
            titleEl.className = "signal-group-title";
            titleEl.textContent = titles[cppnType];
            group.appendChild(titleEl);
            const checkboxesWrap = document.createElement("div");
            checkboxesWrap.className = "signal-checkboxes";
            config[cppnType].toggleableInputs.forEach(function (s) {
                const wrap = document.createElement("div");
                wrap.className =
                    "signal-checkbox" + (s.derived ? " signal-derived" : "");
                const input = document.createElement("input");
                input.type = "checkbox";
                input.id = cppnType + "-" + s.enableKey;
                input.checked = true;
                const label = document.createElement("label");
                label.htmlFor = input.id;
                if (cppnType === "time" && s.enableKey === "rawTime") {
                    label.appendChild(document.createTextNode(s.label + " "));
                    const hint = document.createElement("span");
                    hint.className = "signal-hint";
                    hint.textContent = "(from Time Mode above)";
                    label.appendChild(hint);
                } else if (s.derived) {
                    label.appendChild(document.createTextNode(s.label + " "));
                    const hint = document.createElement("span");
                    hint.className = "signal-hint";
                    hint.textContent = "(from Time CPPN)";
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
        signalState: (function () {
            const state = { time: {}, visual: {} };
            if (
                typeof window !== "undefined" &&
                window.EvolutionConfig &&
                window.EvolutionConfig.SIGNAL_TOGGLES
            ) {
                ["time", "visual"].forEach(function (cppnType) {
                    window.EvolutionConfig.SIGNAL_TOGGLES[
                        cppnType
                    ].toggleableInputs.forEach(function (s) {
                        state[cppnType][s.enableKey] = true;
                    });
                });
            }
            return state;
        })(),
        applyZoom: function () {
            document.documentElement.style.setProperty(
                "--pattern-zoom",
                String(this.patternZoom)
            );
            const label = document.getElementById("zoom-label");
            if (label) label.textContent = Math.round(this.patternZoom * 100) + "%";
        },
        init: function () {
            const self = this;
            const config =
                typeof window !== "undefined" &&
                window.EvolutionConfig &&
                window.EvolutionConfig.SIGNAL_TOGGLES
                    ? window.EvolutionConfig.SIGNAL_TOGGLES
                    : null;
            if (config) {
                populateSignalControls(config);
                ["time", "visual"].forEach(function (cppnType) {
                    config[cppnType].toggleableInputs.forEach(function (s) {
                        const checkbox = document.getElementById(
                            cppnType + "-" + s.enableKey
                        );
                        if (checkbox) {
                            checkbox.addEventListener("change", function (e) {
                                self.signalState[cppnType][s.enableKey] =
                                    e.target.checked;
                            });
                        }
                    });
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
        },
    };

    window.ViewerControls = ViewerControls;
})();

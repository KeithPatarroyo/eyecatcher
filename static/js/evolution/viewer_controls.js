/**
 * Pattern grid zoom and signal checkbox state for representation input toggles.
 * Exposes: ViewerControls.patternZoom, ViewerControls.signalState, ViewerControls.applyZoom(), ViewerControls.init()
 */
(function () {
    "use strict";

    var ZOOM_MIN = 0.5;
    var ZOOM_MAX = 2.0;
    var ZOOM_STEP = 0.1;

    function populateSignalControls(signalGroups) {
        var container = document.getElementById("signal-controls");
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

    class ViewerControls {
        constructor() {
            var config = window.EvolutionConfig;
            this.patternZoom = 1.0;
            this.signalState =
                config && config.getDefaultSignalState
                    ? config.getDefaultSignalState()
                    : {};
        }

        applyZoom() {
            document.documentElement.style.setProperty(
                "--pattern-zoom",
                String(this.patternZoom)
            );
            var label = document.getElementById("zoom-label");
            if (label) label.textContent = Math.round(this.patternZoom * 100) + "%";
        }

        /**
         * Show or hide signal controls based on representation.
         * @param {string|null} representationId - current representation id
         */
        updateForRepresentation(representationId) {
            var container = document.getElementById("signal-controls");
            if (!container) return;
            var representation = window.RepresentationRegistry.get(representationId);
            var show =
                representation === null
                    ? true
                    : representation.hasSignalControls !== false;
            container.style.display = show ? "" : "none";
        }

        init() {
            var self = this;
            var config = window.EvolutionConfig;
            var signalGroups = config && config.SIGNAL_GROUPS;
            var toggleableSignals = config && config.TOGGLEABLE_SIGNALS;
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
                        var checkbox = document.getElementById("signal-" + s.id);
                        if (checkbox) {
                            checkbox.addEventListener("change", function (e) {
                                self.signalState[s.id] = e.target.checked;
                            });
                        }
                    });
                }
            }
            var Utils = window.Utils;
            var zoomIn = document.getElementById("zoom-in");
            var zoomOut = document.getElementById("zoom-out");
            if (zoomIn && Utils && Utils.onRoleButtonKeydown) {
                Utils.onRoleButtonKeydown(zoomIn, function () {
                    self.patternZoom = Math.min(ZOOM_MAX, self.patternZoom + ZOOM_STEP);
                    self.applyZoom();
                });
            }
            if (zoomOut && Utils && Utils.onRoleButtonKeydown) {
                Utils.onRoleButtonKeydown(zoomOut, function () {
                    self.patternZoom = Math.max(ZOOM_MIN, self.patternZoom - ZOOM_STEP);
                    self.applyZoom();
                });
            }
            this.applyZoom();
            var representationId = window.PopulationState.getState().representationId;
            this.updateForRepresentation(representationId);
        }
    }

    window.ViewerControls = new ViewerControls();
})();

/**
 * Debug overlay module for Eyecatcher
 * Provides real-time signal monitoring and time signal output sampling.
 */
const EyecatcherDebug = (function () {
    // Configuration
    let apiUrl = "";
    let getMouseDistanceFn = null; // Function to get mouse distance to a pattern
    let getPatternsMapFn = null; // Function to get the patterns Map
    let getSignalStateFn = null; // Function to get signal state
    let getGenomeForPatternFn = null; // Async function(patternId) => genome JSON for stateless time-output
    let getAdapterFn = null; // Function() => current substrate adapter (for capabilities.timeOutput)

    // State
    let hoveredPatternId = null;
    let timeSamplingEnabled = false;
    let lastSampleTime = 0;
    let lastSampledTimeOutput = null;
    let pendingSampleRequest = false;
    const SAMPLE_INTERVAL_MS = 400;

    // DOM elements (created dynamically)
    let toggleBtn = null;
    let overlay = null;
    let elements = {};

    /**
     * Create the debug overlay DOM structure
     */
    function createDOM() {
        // Toggle button
        toggleBtn = document.createElement("button");
        toggleBtn.id = "debug-toggle";
        toggleBtn.textContent = "Debug";
        document.body.appendChild(toggleBtn);

        // Overlay container (structure from template)
        overlay = document.createElement("div");
        overlay.id = "debug-overlay";
        overlay.className = "hidden";
        const overlayTpl = document.getElementById("debug-overlay-tpl");
        if (overlayTpl && overlayTpl.content) {
            overlay.appendChild(overlayTpl.content.cloneNode(true));
        }
        document.body.appendChild(overlay);

        // Cache element references
        elements = {
            time: document.getElementById("dbg-time"),
            mouseSpeed: document.getElementById("dbg-mouseSpeed"),
            activity: document.getElementById("dbg-activity"),
            mousePos: document.getElementById("dbg-mousePos"),
            patternId: document.getElementById("dbg-pattern-id"),
            mouseDist: document.getElementById("dbg-mouseDist"),
            timeOutput: document.getElementById("dbg-v-time"),
            sampleCheckbox: document.getElementById("dbg-sample-time"),
            sampleWarning: document.getElementById("dbg-sample-warning"),
        };
    }

    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Toggle button
        toggleBtn.addEventListener("click", () => {
            overlay.classList.toggle("hidden");
            toggleBtn.classList.toggle("hidden", !overlay.classList.contains("hidden"));
        });

        // Double-click overlay to close
        overlay.addEventListener("dblclick", () => {
            overlay.classList.add("hidden");
            toggleBtn.classList.remove("hidden");
        });

        // Sample checkbox
        elements.sampleCheckbox.addEventListener("change", (e) => {
            timeSamplingEnabled = e.target.checked;
            elements.sampleWarning.classList.toggle("hidden", !timeSamplingEnabled);
            if (!timeSamplingEnabled) {
                lastSampledTimeOutput = null;
            }
        });
    }

    /**
     * Fetch time output from server (stateless: send genome in body)
     */
    async function sampleTimeOutput(
        patternId,
        time,
        mouseSpd,
        mouseDist,
        activityLevel
    ) {
        if (pendingSampleRequest || !getGenomeForPatternFn) return;

        pendingSampleRequest = true;
        lastSampleTime = performance.now();

        try {
            const genome = await getGenomeForPatternFn(patternId);
            if (!genome) {
                pendingSampleRequest = false;
                return;
            }
            let data;
            try {
                data = await window.ApiClient.apiFetch(
                    apiUrl + "/time-output",
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            genome,
                            time,
                            mouseSpeed: mouseSpd,
                            mouseDist,
                            activity: activityLevel,
                        }),
                    },
                    "Time output failed"
                );
            } catch (_e) {
                pendingSampleRequest = false;
                return;
            }
            if (hoveredPatternId === patternId && timeSamplingEnabled) {
                lastSampledTimeOutput = data.timeOutput;
            }
        } catch (error) {
            console.error("Error sampling time output:", error);
        } finally {
            pendingSampleRequest = false;
        }
    }

    /**
     * Format number for display
     */
    function fmt(v) {
        return v.toFixed(3);
    }

    // Public API
    return {
        /**
         * Initialize the debug module
         * @param {Object} config Configuration object
         * @param {string} config.apiUrl Base API URL
         * @param {Function} config.getMouseDistance Function(canvas) that returns mouse distance to canvas center
         * @param {Function} config.getPatterns Function() that returns the patterns Map
         * @param {Function} config.getSignalState Function() that returns signalState object
         * @param {Function} config.getGenomeForPattern Async function(patternId) that returns genome JSON (for time-output)
         */
        init: function (config) {
            apiUrl = config.apiUrl || "";
            getMouseDistanceFn = config.getMouseDistance || (() => 0);
            getPatternsMapFn = config.getPatterns || (() => new Map());
            getSignalStateFn =
                config.getSignalState || (() => ({ visual: { time: true } }));
            getGenomeForPatternFn = config.getGenomeForPattern || null;
            getAdapterFn = config.getAdapter || null;

            createDOM();
            setupEventListeners();
        },

        /**
         * Update the debug overlay with current values
         * @param {Object} state Current state
         * @param {number} state.time Animation time (0-1)
         * @param {number} state.mouseSpeed Mouse speed (0-1)
         * @param {number} state.activity Activity level (0-1)
         * @param {number} state.mouseX Mouse X position
         * @param {number} state.mouseY Mouse Y position
         */
        update: function (state) {
            // Skip if hidden
            if (overlay.classList.contains("hidden")) return;

            const { time, mouseSpeed, activity, mouseX, mouseY } = state;

            // Global signals
            elements.time.textContent = fmt(time);
            elements.mouseSpeed.textContent = fmt(mouseSpeed);
            elements.activity.textContent = fmt(activity);
            elements.mousePos.textContent = `${Math.round(mouseX)}, ${Math.round(mouseY)}`;

            const timeEl = elements.timeOutput;
            const adapter = getAdapterFn ? getAdapterFn() : null;
            const hasTimeOutput =
                adapter &&
                adapter.capabilities &&
                adapter.capabilities.timeOutput === true;
            const signalState = getSignalStateFn();
            const timeEnabled =
                hasTimeOutput && signalState.visual && signalState.visual.time;

            // Hovered pattern info
            const patterns = getPatternsMapFn();
            if (hoveredPatternId !== null && patterns.has(hoveredPatternId)) {
                const patternData = patterns.get(hoveredPatternId);
                const mouseDist = getMouseDistanceFn(patternData.canvas);

                elements.patternId.textContent = `#${hoveredPatternId}`;
                elements.mouseDist.textContent = fmt(mouseDist);

                // Time output - only when substrate has timeOutput capability
                if (!hasTimeOutput) {
                    timeEl.textContent = "-";
                    timeEl.classList.remove("disabled", "sampled");
                } else if (timeSamplingEnabled && timeEnabled) {
                    const now = performance.now();
                    if (
                        !pendingSampleRequest &&
                        now - lastSampleTime >= SAMPLE_INTERVAL_MS
                    ) {
                        sampleTimeOutput(
                            hoveredPatternId,
                            time,
                            mouseSpeed,
                            mouseDist,
                            activity
                        );
                    }
                    if (lastSampledTimeOutput !== null) {
                        timeEl.textContent = fmt(lastSampledTimeOutput);
                        timeEl.classList.remove("disabled");
                        timeEl.classList.add("sampled");
                    } else {
                        timeEl.textContent = "...";
                        timeEl.classList.remove("disabled", "sampled");
                    }
                } else {
                    timeEl.textContent = timeEnabled ? "unique" : "disabled";
                    timeEl.classList.toggle("disabled", !timeEnabled);
                    timeEl.classList.remove("sampled");
                }
            } else {
                elements.patternId.textContent = "(hover to see)";
                elements.mouseDist.textContent = "-";
                timeEl.textContent = "-";
                timeEl.classList.remove("disabled", "sampled");
                lastSampledTimeOutput = null;
            }
        },

        /**
         * Set the currently hovered pattern ID
         * Called from main script on card mouseenter/mouseleave
         * @param {number|null} id Pattern ID or null if not hovering
         */
        setHoveredPatternId: function (id) {
            if (id !== hoveredPatternId) {
                lastSampledTimeOutput = null; // Reset sample when changing patterns
            }
            hoveredPatternId = id;
        },

        /**
         * Get the currently hovered pattern ID
         * @returns {number|null}
         */
        getHoveredPatternId: function () {
            return hoveredPatternId;
        },

        /**
         * Show or hide time-output section based on substrate capabilities.
         * Call when substrate changes (e.g. after load or addToGrid).
         * @param {string|null} substrateId - current substrate id
         */
        updateForSubstrate: function (substrateId) {
            const adapter =
                typeof window !== "undefined" &&
                window.SubstrateAdapters &&
                window.SubstrateAdapters.getAdapter
                    ? window.SubstrateAdapters.getAdapter(substrateId)
                    : null;
            const show =
                adapter &&
                adapter.capabilities &&
                adapter.capabilities.timeOutput === true;
            const section = document.getElementById("debug-time-output-section");
            if (section) section.style.display = show ? "" : "none";
        },
    };
})();
if (typeof window !== "undefined") {
    window.EyecatcherDebug = EyecatcherDebug;
}

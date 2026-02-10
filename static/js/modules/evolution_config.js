/**
 * Evolution and viewer constants. Single place for frontend defaults that align with the backend.
 * Load before: api_client, app_core, toolbar_ui.
 * Exposes: window.EvolutionConfig
 */
(function () {
    "use strict";

    var EvolutionConfig = {
        // Population (must match backend evolution/config.py)
        DEFAULT_POPULATION_SIZE: 12,
        MAX_POPULATION_SIZE: 50,
        MIN_POPULATION_SIZE: 2,

        // Fullscreen / canvas (viewer-only; backend uses DEFAULT_RENDER_RESOLUTION for saves)
        FULLSCREEN_CANVAS_DEFAULT: 800,
        FULLSCREEN_CANVAS_MAX: 1024,
        FULLSCREEN_CANVAS_MIN: 64,

        // Dev server (api_client fallback when not served from same origin)
        DEFAULT_DEV_PORT: 5001,

        // Signal registry (mirror backend evolution/signals.py; toggleable inputs only, no spatial/bias)
        SIGNALS: {
            time: {
                inputs: [
                    {
                        name: "rawTime",
                        uniform: "uTime",
                        label: "Raw Time",
                        enableKey: "rawTime",
                    },
                    {
                        name: "mouseSpeed",
                        uniform: "uMouseSpeed",
                        label: "Mouse Speed",
                        enableKey: "mouseSpeed",
                    },
                    {
                        name: "mouseDist",
                        uniform: "uMouseDist",
                        label: "Mouse Dist",
                        enableKey: "mouseDist",
                    },
                    {
                        name: "inactivity",
                        uniform: "uInactivity",
                        label: "Activity",
                        enableKey: "inactivity",
                    },
                ],
            },
            visual: {
                inputs: [
                    {
                        name: "time",
                        uniform: null,
                        label: "Body Clock",
                        enableKey: "time",
                        derived: true,
                    },
                    {
                        name: "mouseSpeed",
                        uniform: "uMouseSpeed",
                        label: "Mouse Speed",
                        enableKey: "mouseSpeed",
                    },
                    {
                        name: "mouseDist",
                        uniform: "uMouseDist",
                        label: "Mouse Dist",
                        enableKey: "mouseDist",
                    },
                    {
                        name: "inactivity",
                        uniform: "uInactivity",
                        label: "Activity",
                        enableKey: "inactivity",
                    },
                ],
            },
        },
        OUTPUTS: {
            visual: [
                { name: "red", label: "Red" },
                { name: "green", label: "Green" },
                { name: "blue", label: "Blue" },
            ],
            time: [{ name: "modified_time", label: "Modified Time" }],
        },
        // Full input labels for network viz (order matches backend; includes spatial/bias)
        NETWORK_INPUT_LABELS: {
            time: ["rawTime", "mSpeed", "mDist", "inact", "bias"],
            visual: ["x", "y", "dist", "time", "mSpeed", "mDist", "inact", "bias"],
        },
    };

    if (typeof window !== "undefined") {
        window.EvolutionConfig = EvolutionConfig;
    }
})();

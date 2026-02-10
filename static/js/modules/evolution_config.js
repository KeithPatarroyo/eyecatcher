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
    };

    if (typeof window !== "undefined") {
        window.EvolutionConfig = EvolutionConfig;
    }
})();

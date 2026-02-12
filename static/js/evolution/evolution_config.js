/**
 * Evolution and viewer constants. Single place for frontend defaults that align with the backend.
 * Signal toggles and outputs come from evolution_config_signals.generated.js (generated from Python registry).
 * Load before: api_client, app_core, toolbar_ui. Load after: evolution_config_signals.generated.js.
 * Exposes: window.EvolutionConfig
 */
(function () {
    "use strict";

    var signals = window.EvolutionConfigSignals || null;

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

        // From generated config (Python registry) or fallback for dev without codegen
        SIGNAL_TOGGLES: signals
            ? signals.SIGNAL_TOGGLES
            : {
                  time: { toggleableInputs: [] },
                  visual: { toggleableInputs: [] },
              },
        OUTPUTS: signals
            ? signals.OUTPUTS
            : {
                  visual: [],
                  time: [],
              },
    };

    /**
     * Merge server config (from GET /api/config) into EvolutionConfig.
     * Call after fetchConfig() so population limits match the active preset.
     * @param {Object} config - { population_size, max_population_size }
     */
    EvolutionConfig.mergeFromServer = function (config) {
        if (!config) return;
        if (config.population_size != null) {
            this.DEFAULT_POPULATION_SIZE = config.population_size;
        }
        if (config.max_population_size != null) {
            this.MAX_POPULATION_SIZE = config.max_population_size;
        }
    };

    window.EvolutionConfig = EvolutionConfig;
})();

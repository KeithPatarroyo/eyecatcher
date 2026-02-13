/**
 * Evolution and viewer constants. Population defaults from evolution_config_defaults.generated.js
 * (generated from config/evolution_defaults.json; run make generate). mergeFromServer overwrites from API.
 * Load before: api_client, app_core, toolbar_ui. Load after: evolution_config_signals.generated.js, evolution_config_defaults.generated.js.
 * Exposes: window.EvolutionConfig
 */
(function () {
    "use strict";

    var signals = window.EvolutionConfigSignals || null;
    if (!signals) {
        console.warn(
            "EvolutionConfigSignals not loaded (run scripts/generate_signal_config.py). Signal toggles will be empty."
        );
    }

    var defaults = window.EvolutionConfigDefaults;
    if (!defaults) {
        console.error(
            "EvolutionConfigDefaults not loaded (run make generate-evolution-config)."
        );
        defaults = {};
    }

    var EvolutionConfig = {
        // Population (from evolution_config_defaults.generated.js; run make generate)
        DEFAULT_POPULATION_SIZE: defaults.population_size,
        MAX_POPULATION_SIZE: defaults.max_population_size,
        MIN_POPULATION_SIZE: defaults.min_population_size,
        CROSSOVER_PROBABILITY: defaults.crossover_probability,

        // Representation (backend returns representation_id; we expose as substrateId for UI)
        DEFAULT_SUBSTRATE_ID: "dual_cppn",
        /** Available representation ids from GET /api/config (e.g. ["dual_cppn", "single_cppn", "ca"]). */
        available_substrate_ids: [],

        /** Single source of truth for default resolution when adapter cannot be determined. */
        getDefaultResolution: function () {
            return {
                outputType: "shader",
                substrateId: this.DEFAULT_SUBSTRATE_ID,
            };
        },

        // Fullscreen / canvas (viewer-only; backend uses DEFAULT_RENDER_RESOLUTION for saves)
        FULLSCREEN_CANVAS_DEFAULT: 800,
        FULLSCREEN_CANVAS_MAX: 1024,
        FULLSCREEN_CANVAS_MIN: 64,

        // Dev server (api_client fallback when not served from same origin)
        DEFAULT_DEV_PORT: 5001,

        // From generated config (Python registry) or fallback for dev without codegen
        SIGNAL_GROUPS: signals ? signals.SIGNAL_GROUPS : [],
        TOGGLEABLE_SIGNALS: signals ? signals.TOGGLEABLE_SIGNALS : [],
        OUTPUTS: signals ? signals.OUTPUTS : [],
        SIGNAL_IDS: signals ? signals.SIGNAL_IDS : [],
    };

    /**
     * Default signal state: all toggleable inputs enabled (true). Flat { signal_id: boolean }.
     * @returns {Object<string, boolean>}
     */
    EvolutionConfig.getDefaultSignalState = function () {
        var list = this.TOGGLEABLE_SIGNALS || [];
        var state = {};
        list.forEach(function (s) {
            state[s.id] = true;
        });
        return state;
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
        if (config.crossover_probability != null) {
            this.CROSSOVER_PROBABILITY = config.crossover_probability;
        }
        if (config.representation_id != null) {
            this.DEFAULT_SUBSTRATE_ID = config.representation_id;
        }
        if (Array.isArray(config.available_representation_ids)) {
            this.available_substrate_ids = config.available_representation_ids;
        }
    };

    window.EvolutionConfig = EvolutionConfig;
})();

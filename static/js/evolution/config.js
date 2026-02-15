/**
 * Evolution and viewer constants. Population defaults from config/evolution_defaults.json
 * (run make generate). mergeFromServer overwrites from API.
 * Reads from window.EyecatcherConfig (single config.generated.js) or legacy globals.
 * Exposes: window.EvolutionConfig
 */
(function () {
    "use strict";

    var unified = window.EyecatcherConfig;
    var signals = (unified && unified.signals) || window.EvolutionConfigSignals || null;
    if (!signals) {
        console.warn(
            "Signal config not loaded (run make generate). Signal toggles will be empty."
        );
    }

    var defaults = (unified && unified.defaults) || window.EvolutionConfigDefaults;
    if (!defaults) {
        console.error("Defaults not loaded (run make generate).");
        defaults = {};
    }

    var EvolutionConfig = {
        // Population (from EyecatcherConfig.defaults or config_defaults.generated.js)
        DEFAULT_POPULATION_SIZE: defaults.population_size,
        MAX_POPULATION_SIZE: defaults.max_population_size,
        MIN_POPULATION_SIZE: defaults.min_population_size,
        CROSSOVER_PROBABILITY: defaults.crossover_probability,

        // Representation (backend returns representation_id; we expose as representationId for UI)
        // Initial value; overwritten by mergeFromServer. Canonical default is in representation/registry.js (resolve / getDefaultRepresentationId).
        DEFAULT_REPRESENTATION_ID: "",
        /** Available representation ids from GET /api/config (e.g. ["dual_cppn", "single_cppn", "ca"]). */
        available_representation_ids: [],

        /** Single source of truth for default resolution. Uses __eyecatcherDefaultResolution (set by registry) for fallback; do not call RA.getDefaultResolution to avoid circular recursion. */
        getDefaultResolution: function () {
            var def = window.__eyecatcherDefaultResolution;
            return {
                representationId:
                    this.DEFAULT_REPRESENTATION_ID ||
                    (def && def.representationId) ||
                    "",
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
            this.DEFAULT_REPRESENTATION_ID = config.representation_id;
        }
        if (Array.isArray(config.available_representation_ids)) {
            this.available_representation_ids = config.available_representation_ids;
        }
    };

    window.EvolutionConfig = EvolutionConfig;
})();

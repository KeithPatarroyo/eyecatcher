// experiment_config.js (replace whole file)
const unified = window.EyecatcherConfig ?? {};
const defaults = unified.defaults ?? {};
let signalsByRepresentation = unified.signals;

if (!signalsByRepresentation || typeof signalsByRepresentation !== "object") {
    console.warn(
        "Signal config not loaded or wrong shape (run make generate). Signal toggles will be empty."
    );
    signalsByRepresentation = {};
}

if (!unified.defaults) console.error("Defaults not loaded (run make generate).");

const entryFor = (repId) => (repId ? signalsByRepresentation[repId] : null) ?? null;

const EvolutionConfig = {
    // Population (generated defaults; may be overwritten by mergeFromServer)
    DEFAULT_POPULATION_SIZE: defaults.population_size,
    MAX_POPULATION_SIZE: defaults.max_population_size,
    MIN_POPULATION_SIZE: defaults.min_population_size,
    CROSSOVER_PROBABILITY: defaults.crossover_probability,

    // Representation
    DEFAULT_REPRESENTATION_ID: "",
    available_representation_ids: [],

    // Viewer-only
    FULLSCREEN_CANVAS_DEFAULT: 800,
    FULLSCREEN_CANVAS_MAX: 1024,
    FULLSCREEN_CANVAS_MIN: 64,
    DEFAULT_DEV_PORT: 5001,

    // Signals
    signalsByRepresentation,

    getDefaultResolution() {
        const def = window.__eyecatcherDefaultResolution;
        return {
            representationId:
                this.DEFAULT_REPRESENTATION_ID || def?.representationId || "",
        };
    },

    getCurrentRepresentationId() {
        const state = window.PopulationState?.getState?.();
        return (
            state?.representationId ||
            this.getDefaultResolution().representationId ||
            ""
        );
    },

    getSignalGroups(representationId) {
        return entryFor(representationId)?.SIGNAL_GROUPS ?? [];
    },

    getToggleableSignals(representationId) {
        return entryFor(representationId)?.TOGGLEABLE_SIGNALS ?? [];
    },

    getSignalIds(representationId) {
        return entryFor(representationId)?.SIGNAL_IDS ?? [];
    },

    getOutputs(representationId) {
        return entryFor(representationId)?.OUTPUTS ?? [];
    },

    getDefaultSignalState(representationId) {
        const state = {};
        for (const s of this.getToggleableSignals(representationId)) state[s.id] = true;
        return state;
    },

    // Convenience for current rep
    getSignalGroupsForCurrentRep() {
        return this.getSignalGroups(this.getCurrentRepresentationId());
    },
    getToggleableSignalsForCurrentRep() {
        return this.getToggleableSignals(this.getCurrentRepresentationId());
    },
    getSignalIdsForCurrentRep() {
        return this.getSignalIds(this.getCurrentRepresentationId());
    },
    getDefaultSignalStateForCurrentRep() {
        return this.getDefaultSignalState(this.getCurrentRepresentationId());
    },

    mergeFromServer(config) {
        if (!config) return;

        if (config.population_size != null)
            this.DEFAULT_POPULATION_SIZE = config.population_size;
        if (config.max_population_size != null)
            this.MAX_POPULATION_SIZE = config.max_population_size;
        if (config.crossover_probability != null)
            this.CROSSOVER_PROBABILITY = config.crossover_probability;

        if (config.representation_id != null)
            this.DEFAULT_REPRESENTATION_ID = config.representation_id;
        if (Array.isArray(config.available_representation_ids))
            this.available_representation_ids = config.available_representation_ids;
    },
};

/**
 * Single accessor for app config. Always returns the same object; use assertConfig() at startup to validate.
 */
const getConfig = () => EvolutionConfig;

/**
 * Call once at app init. Logs loudly if required config is missing; does not throw so app can still run with defaults.
 */
const assertConfig = () => {
    if (!unified.defaults) {
        console.error(
            "[EvolutionConfig] Defaults not loaded. Run 'make generate' or ensure config.generated.js is loaded."
        );
    }
    if (!signalsByRepresentation || typeof signalsByRepresentation !== "object") {
        console.warn(
            "[EvolutionConfig] Signal config missing or wrong shape. Signal toggles may be empty."
        );
    }
};

export { EvolutionConfig, getConfig, assertConfig };
window.EvolutionConfig = EvolutionConfig;
window.getConfig = getConfig;
window.assertConfig = assertConfig;

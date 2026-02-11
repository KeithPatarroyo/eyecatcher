/**
 * PopulationState: single source of truth for current population and genealogy context.
 * No DOM; used by app.js and coordinators. Researchers extend evolution/interaction via
 * BreedCoordinator and state actions.
 *
 * Load after: utils (optional, for storage helpers if needed).
 * Exposes: PopulationState.init, PopulationState.getState, PopulationState.dispatch, PopulationState.subscribe.
 */
(function () {
    "use strict";

    var state = {
        currentPopulation: [],
        currentGenomes: null,
        generationNum: 0,
        populationId: null,
        branchName: "main",
        patterns: new Map(),
        loading: false,
        error: null,
    };

    var subscribers = [];

    function getState() {
        return {
            currentPopulation: state.currentPopulation,
            currentGenomes: state.currentGenomes,
            generationNum: state.generationNum,
            populationId: state.populationId,
            branchName: state.branchName,
            patterns: state.patterns,
            loading: state.loading,
            error: state.error,
        };
    }

    function dispatch(action) {
        switch (action.type) {
            case "LOAD_POPULATION":
                state.currentPopulation = action.payload.population || [];
                state.currentGenomes = action.payload.genomes || null;
                state.generationNum =
                    action.payload.generationNum ?? state.generationNum;
                if (action.payload.populationId !== undefined) {
                    state.populationId = action.payload.populationId;
                }
                if (action.payload.branchName !== undefined) {
                    state.branchName = action.payload.branchName;
                }
                state.patterns.clear();
                if (action.payload.patternsMap) {
                    action.payload.patternsMap.forEach(function (v, k) {
                        state.patterns.set(k, v);
                    });
                }
                state.loading = false;
                state.error = null;
                break;
            case "ADD_TO_GRID":
                state.currentGenomes = (state.currentGenomes || []).concat(
                    action.payload.genomes || []
                );
                state.currentPopulation = (state.currentPopulation || []).concat(
                    action.payload.population || []
                );
                if (action.payload.patternsMap) {
                    action.payload.patternsMap.forEach(function (v, k) {
                        state.patterns.set(k, v);
                    });
                }
                state.loading = false;
                break;
            case "SET_PATTERN_CLICKS":
                if (state.patterns.has(action.payload.id)) {
                    var p = state.patterns.get(action.payload.id);
                    p.clicks = action.payload.clicks;
                }
                break;
            case "SET_EVOLVE_RESULT":
                if (action.payload.populationId != null) {
                    state.populationId = action.payload.populationId;
                }
                break;
            case "SET_LOADING":
                state.loading = action.payload !== undefined ? action.payload : true;
                break;
            case "SET_ERROR":
                state.error = action.payload;
                state.loading = false;
                break;
            case "UPDATE_PATTERN_SHADER":
                if (state.patterns.has(action.payload.id)) {
                    state.patterns.set(action.payload.id, action.payload.patternData);
                }
                break;
            case "SET_GENEALOGY":
                state.populationId = action.payload.populationId;
                state.branchName = action.payload.branchName || "main";
                break;
            case "UPDATE_GENOME_AT_INDEX":
                if (
                    state.currentGenomes &&
                    action.payload.idx >= 0 &&
                    action.payload.idx < state.currentGenomes.length
                ) {
                    state.currentGenomes[action.payload.idx] = action.payload.genome;
                }
                break;
            case "CLEAR":
                state.currentPopulation = [];
                state.currentGenomes = null;
                state.generationNum = 0;
                state.populationId = null;
                state.branchName = "main";
                state.patterns.clear();
                state.loading = false;
                state.error = null;
                break;
            default:
                return;
        }
        subscribers.forEach(function (cb) {
            try {
                cb(getState());
            } catch (e) {
                console.warn("PopulationState subscriber error:", e);
            }
        });
    }

    function init() {
        state.currentPopulation = [];
        state.currentGenomes = null;
        state.generationNum = 0;
        state.populationId = null;
        state.branchName = "main";
        state.patterns = new Map();
        state.loading = false;
        state.error = null;
    }

    function subscribe(callback) {
        if (typeof callback === "function") {
            subscribers.push(callback);
        }
        return function unsubscribe() {
            var i = subscribers.indexOf(callback);
            if (i !== -1) subscribers.splice(i, 1);
        };
    }

    window.PopulationState = {
        init: init,
        getState: getState,
        dispatch: dispatch,
        subscribe: subscribe,
    };
})();

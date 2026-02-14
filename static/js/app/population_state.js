/**
 * PopulationState: single source of truth for current population and genealogy context.
 * No DOM; used by app.js and coordinators. Researchers extend evolution/interaction via
 * BreedCoordinator and state actions.
 *
 * Exposes: PopulationState.getState, PopulationState.dispatch, PopulationState.subscribe, PopulationState.init.
 */
(function () {
    "use strict";

    class PopulationState {
        constructor() {
            this._state = {
                currentPopulation: [],
                currentGenomes: null,
                generationNum: 0,
                populationId: null,
                branchName: "main",
                substrateId: null,
                outputType: "shader",
                patterns: new Map(),
                loading: false,
                error: null,
            };
            this._subscribers = [];
        }

        getState() {
            var s = this._state;
            return {
                currentPopulation: s.currentPopulation,
                currentGenomes: s.currentGenomes,
                generationNum: s.generationNum,
                populationId: s.populationId,
                branchName: s.branchName,
                substrateId: s.substrateId,
                outputType: s.outputType,
                patterns: s.patterns,
                loading: s.loading,
                error: s.error,
            };
        }

        get substrateId() {
            return this._state.substrateId;
        }
        get outputType() {
            return this._state.outputType;
        }
        get patterns() {
            return this._state.patterns;
        }
        get currentGenomes() {
            return this._state.currentGenomes;
        }
        get currentPopulation() {
            return this._state.currentPopulation;
        }
        get branchName() {
            return this._state.branchName;
        }
        get populationId() {
            return this._state.populationId;
        }
        get generationNum() {
            return this._state.generationNum;
        }

        dispatch(action) {
            var state = this._state;
            var payload = action.payload;

            switch (action.type) {
                case "LOAD_POPULATION":
                    state.currentPopulation = payload.population || [];
                    state.currentGenomes = payload.genomes || null;
                    state.generationNum = payload.generationNum ?? state.generationNum;
                    if (payload.populationId !== undefined) {
                        state.populationId = payload.populationId;
                    }
                    if (payload.branchName !== undefined) {
                        state.branchName = payload.branchName;
                    }
                    if (payload.substrateId !== undefined) {
                        state.substrateId = payload.substrateId;
                    }
                    if (payload.outputType !== undefined) {
                        state.outputType = payload.outputType;
                    }
                    state.patterns.clear();
                    if (payload.patternsMap) {
                        payload.patternsMap.forEach(function (v, k) {
                            state.patterns.set(k, v);
                        });
                    }
                    state.loading = false;
                    state.error = null;
                    break;
                case "ADD_TO_GRID":
                    state.currentGenomes = (state.currentGenomes || []).concat(
                        payload.genomes || []
                    );
                    state.currentPopulation = (state.currentPopulation || []).concat(
                        payload.population || []
                    );
                    if (payload.substrateId !== undefined) {
                        state.substrateId = payload.substrateId;
                    }
                    if (payload.outputType !== undefined) {
                        state.outputType = payload.outputType;
                    }
                    if (payload.patternsMap) {
                        payload.patternsMap.forEach(function (v, k) {
                            state.patterns.set(k, v);
                        });
                    }
                    state.loading = false;
                    break;
                case "SET_PATTERN_CLICKS":
                    if (state.patterns.has(payload.id)) {
                        var p = state.patterns.get(payload.id);
                        p.clicks = payload.clicks;
                    }
                    break;
                case "SET_EVOLVE_RESULT":
                    if (payload.populationId != null) {
                        state.populationId = payload.populationId;
                    }
                    break;
                case "SET_LOADING":
                    state.loading = payload !== undefined ? payload : true;
                    break;
                case "SET_ERROR":
                    state.error = payload;
                    state.loading = false;
                    break;
                case "UPDATE_PATTERN_SHADER":
                    if (state.patterns.has(payload.id)) {
                        state.patterns.set(payload.id, payload.patternData);
                    }
                    break;
                case "SET_GENEALOGY":
                    state.populationId = payload.populationId;
                    state.branchName = payload.branchName || "main";
                    break;
                case "UPDATE_GENOME_AT_INDEX":
                    if (
                        state.currentGenomes &&
                        payload.idx >= 0 &&
                        payload.idx < state.currentGenomes.length
                    ) {
                        state.currentGenomes[payload.idx] = payload.genome;
                    }
                    break;
                case "CLEAR":
                    state.currentPopulation = [];
                    state.currentGenomes = null;
                    state.generationNum = 0;
                    state.populationId = null;
                    state.branchName = "main";
                    state.substrateId = null;
                    state.outputType = "shader";
                    state.patterns.clear();
                    state.loading = false;
                    state.error = null;
                    break;
                default:
                    return;
            }
            var self = this;
            this._subscribers.forEach(function (cb) {
                try {
                    cb(self.getState());
                } catch (e) {
                    console.warn("PopulationState subscriber error:", e);
                }
            });
        }

        init() {
            this._state.currentPopulation = [];
            this._state.currentGenomes = null;
            this._state.generationNum = 0;
            this._state.populationId = null;
            this._state.branchName = "main";
            this._state.substrateId = null;
            this._state.outputType = "shader";
            this._state.patterns = new Map();
            this._state.loading = false;
            this._state.error = null;
        }

        subscribe(callback) {
            if (typeof callback === "function") {
                this._subscribers.push(callback);
            }
            var self = this;
            return function unsubscribe() {
                var i = self._subscribers.indexOf(callback);
                if (i !== -1) self._subscribers.splice(i, 1);
            };
        }
    }

    window.PopulationState = new PopulationState();
})();

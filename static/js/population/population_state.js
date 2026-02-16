/**
 * PopulationState: single source of truth for current population and genealogy context.
 * Canonical state is organisms array. Use getOrganism(id), getGenomes(), getPhenotypes() for derived data.
 *
 * Exposes: PopulationState.getState, getOrganism, getGenomes, getPhenotypes, dispatch, subscribe, init.
 */
(function () {
    "use strict";

    function payloadToOrganisms(population, genomes, patternsMap) {
        if (!population || !genomes) {
            console.error(
                "Add to grid: payloadToOrganisms missing population or genomes"
            );
            return [];
        }
        if (population.length !== genomes.length) {
            console.error(
                "Add to grid: payloadToOrganisms length mismatch – population " +
                    population.length +
                    ", genomes " +
                    genomes.length +
                    "; new organisms will not be added"
            );
            return [];
        }
        var map = patternsMap || new Map();
        return population.map(function (p, i) {
            var id = p.id != null ? p.id : genomes[i] && genomes[i].key;
            var runtime = map.get(id) || null;
            if (runtime === null && map.size > 0) {
                console.warn(
                    "Add to grid: no runtime for organism id=" +
                        id +
                        " (index " +
                        i +
                        ") – card may not animate"
                );
            }
            return {
                id: id,
                genome: genomes[i],
                phenotype: p,
                runtime: runtime,
                fitness: p.fitness != null ? p.fitness : 0,
            };
        });
    }

    class PopulationState {
        constructor() {
            this._state = {
                organisms: [],
                generationNum: 0,
                populationId: null,
                branchName: "main",
                representationId: null,
                loading: false,
                error: null,
            };
            this._subscribers = [];
        }

        getState() {
            var s = this._state;
            return {
                organisms: s.organisms,
                generationNum: s.generationNum,
                populationId: s.populationId,
                branchName: s.branchName,
                representationId: s.representationId,
                loading: s.loading,
                error: s.error,
            };
        }

        getOrganism(id) {
            return this._state.organisms.find(function (o) {
                return o.id === id;
            });
        }

        getGenomes() {
            return this._state.organisms.map(function (o) {
                return o.genome;
            });
        }

        getPhenotypes() {
            return this._state.organisms.map(function (o) {
                return o.phenotype;
            });
        }

        get representationId() {
            return this._state.representationId;
        }
        get organisms() {
            return this._state.organisms;
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
                    if (payload.organisms && Array.isArray(payload.organisms)) {
                        state.organisms = payload.organisms;
                    } else {
                        state.organisms = payloadToOrganisms(
                            payload.population || [],
                            payload.genomes || [],
                            payload.patternsMap
                        );
                    }
                    state.generationNum = payload.generationNum ?? state.generationNum;
                    if (payload.populationId !== undefined) {
                        state.populationId = payload.populationId;
                    }
                    if (payload.branchName !== undefined) {
                        state.branchName = payload.branchName;
                    }
                    if (payload.representationId !== undefined) {
                        state.representationId = payload.representationId;
                    }
                    state.loading = false;
                    state.error = null;
                    break;
                case "ADD_TO_GRID":
                    state.organisms = state.organisms.concat(
                        payloadToOrganisms(
                            payload.population || [],
                            payload.genomes || [],
                            payload.patternsMap
                        )
                    );
                    if (payload.representationId !== undefined) {
                        state.representationId = payload.representationId;
                    }
                    state.loading = false;
                    break;
                case "SET_ORGANISM_FITNESS": {
                    var o = state.organisms.find(function (x) {
                        return x.id === payload.id;
                    });
                    if (o) {
                        o.fitness = payload.fitness;
                        if (o.runtime) o.runtime.fitness = payload.fitness;
                    }
                    break;
                }
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
                case "UPDATE_PATTERN_RULE": {
                    var o2 = state.organisms.find(function (x) {
                        return x.id === payload.id;
                    });
                    if (o2) o2.runtime = payload.runtime;
                    break;
                }
                case "SET_GENEALOGY":
                    state.populationId = payload.populationId;
                    state.branchName = payload.branchName || "main";
                    break;
                case "UPDATE_GENOME_AT_INDEX":
                    if (payload.idx >= 0 && payload.idx < state.organisms.length) {
                        state.organisms[payload.idx].genome = payload.genome;
                    }
                    break;
                case "CLEAR":
                    state.organisms = [];
                    state.generationNum = 0;
                    state.populationId = null;
                    state.branchName = "main";
                    state.representationId = null;
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
            this._state.organisms = [];
            this._state.generationNum = 0;
            this._state.populationId = null;
            this._state.branchName = "main";
            this._state.representationId = null;
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

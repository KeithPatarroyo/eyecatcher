/**
 * PopulationLoader: orchestrates loading and adding population (fetch display data, render grid, dispatch state, optional genealogy save).
 * Depends on GridRenderer, DisplayFetcher, PopulationState, GenealogySync, RepresentationRegistry (via deps.resolveRepresentation).
 * Exposes: init, loadPopulation, addToPopulation.
 */
(function () {
    "use strict";

    var _deps = null;

    function init(deps) {
        _deps = deps;
    }

    /**
     * Load a population from genomes: fetch display data, render grid, dispatch LOAD_POPULATION, optionally save to genealogy.
     * @param {Array} genomes
     * @param {number} generationNum
     * @param {string} representationId
     * @param {{ saveToGenealogy?: boolean }} options
     * @returns {Promise<void>}
     */
    function loadPopulation(genomes, generationNum, representationId, options) {
        options = options || {};
        var saveToGenealogy = options.saveToGenealogy === true;
        if (!_deps || !genomes || !genomes.length) {
            return Promise.resolve();
        }
        var resolved = _deps.resolveRepresentation(representationId, genomes);
        var resolvedRepresentationId = resolved.representationId;
        var representation = resolved.representation;
        if (!representation) {
            window.GridRenderer.showGridError(
                "No representation for " +
                    (resolvedRepresentationId || "?") +
                    ". Check config.",
                false
            );
            if (_deps.showLoading) _deps.showLoading(false);
            window.PopulationState.dispatch({
                type: "SET_LOADING",
                payload: false,
            });
            return Promise.resolve();
        }
        return window.Utils.withLoading(function () {
            window.GridRenderer.clearGrid(_deps.IDS);
            return window.DisplayFetcher.fetchDisplayData(representation, genomes, {
                colorMode: _deps.getColorMode(),
            })
                .then(function (displayResult) {
                    var population =
                        displayResult.population || displayResult.shaders || [];
                    if (!population.length) {
                        window.GridRenderer.showGridError(
                            "No patterns returned from server.",
                            true
                        );
                        return {
                            population: [],
                            patternsMap: new Map(),
                        };
                    }
                    var patternsMap = new Map();
                    window.GridRenderer.renderGridFromPopulation(
                        population,
                        _deps.IDS,
                        _deps.getGridCallbacks(),
                        patternsMap,
                        resolvedRepresentationId
                    );
                    var branchName = window.PopulationState.branchName || "main";
                    var parentId = window.PopulationState.populationId;
                    if (saveToGenealogy) {
                        if (generationNum === 0) {
                            parentId = null;
                            window.GenealogySync.syncCurrentPopulationIdToStorage(null);
                            var counter =
                                window.GenealogySync.getGenealogyBranchCounter();
                            branchName = counter === 1 ? "main" : "branch-" + counter;
                            window.GenealogySync.setGenealogyBranchCounter(counter + 1);
                            window.PopulationState.dispatch({
                                type: "SET_GENEALOGY",
                                payload: {
                                    populationId: null,
                                    branchName: branchName,
                                },
                            });
                        }
                        var fitnessData = population.map(function (p) {
                            var pat = patternsMap.get(p.id);
                            return pat ? pat.fitness || 0 : 0;
                        });
                        return window.GenealogySync.saveCurrentPopulationToGenealogy(
                            _deps.API_URL,
                            genomes,
                            generationNum,
                            branchName,
                            parentId,
                            fitnessData,
                            window.ApiClient.apiFetch,
                            resolvedRepresentationId
                        )
                            .then(function (data) {
                                if (data && data.population_id != null) {
                                    window.PopulationState.dispatch({
                                        type: "SET_EVOLVE_RESULT",
                                        payload: {
                                            populationId: data.population_id,
                                        },
                                    });
                                    window.GenealogySync.syncCurrentPopulationIdToStorage(
                                        data.population_id
                                    );
                                }
                            })
                            .catch(function (e) {
                                console.warn("Genealogy save failed:", e);
                            })
                            .then(function () {
                                return {
                                    population: population,
                                    patternsMap: patternsMap,
                                };
                            });
                    }
                    return {
                        population: population,
                        patternsMap: patternsMap,
                    };
                })
                .then(function (result) {
                    var population = result.population;
                    var patternsMap = result.patternsMap;
                    window.PopulationState.dispatch({
                        type: "LOAD_POPULATION",
                        payload: {
                            population: population,
                            genomes: genomes,
                            generationNum: generationNum,
                            patternsMap: patternsMap,
                            representationId: resolvedRepresentationId,
                        },
                    });
                    if (
                        window.ViewerControls &&
                        window.ViewerControls.updateForRepresentation
                    ) {
                        window.ViewerControls.updateForRepresentation(
                            resolvedRepresentationId
                        );
                    }
                    if (
                        window.EyecatcherDebug &&
                        window.EyecatcherDebug.updateForRepresentation
                    ) {
                        window.EyecatcherDebug.updateForRepresentation(
                            resolvedRepresentationId
                        );
                    }
                    var genEl = document.getElementById(_deps.IDS.genNum);
                    if (genEl) genEl.textContent = generationNum;
                    if (_deps.updateStats) _deps.updateStats();
                })
                .catch(function (e) {
                    window.GridRenderer.showGridError(
                        e.message || "Failed to compile",
                        true
                    );
                });
        });
    }

    /**
     * Add genomes to current population: fetch display data, append to grid, dispatch ADD_TO_GRID.
     * @param {Array} genomes
     * @returns {Promise<void>}
     */
    function addToPopulation(genomes) {
        if (!_deps || !genomes || !genomes.length) return Promise.resolve();
        var resolved = _deps.resolveRepresentation(
            window.PopulationState.representationId,
            genomes
        );
        var representation = resolved.representation;
        var nextKey = 0;
        window.PopulationState.organisms.forEach(function (o) {
            var id = o.id;
            if (typeof id === "number" && !isNaN(id)) {
                nextKey = Math.max(nextKey, id + 1);
            }
        });
        var payload = genomes.map(function (g) {
            var copy = Object.assign({}, g);
            copy.key = nextKey++;
            copy.fitness = 0;
            return copy;
        });
        return window.Utils.withLoading(function () {
            return window.DisplayFetcher.fetchDisplayData(representation, payload, {
                colorMode: _deps.getColorMode(),
            })
                .then(function (displayResult) {
                    var population = displayResult.population || [];
                    var newPatternsMap = new Map();
                    window.GridRenderer.appendCardsToGrid(
                        population,
                        _deps.IDS,
                        _deps.getGridCallbacks(),
                        newPatternsMap,
                        window.PopulationState.representationId
                    );
                    window.PopulationState.dispatch({
                        type: "ADD_TO_GRID",
                        payload: {
                            genomes: payload,
                            population: population,
                            patternsMap: newPatternsMap,
                            representationId: resolved.representationId,
                        },
                    });
                    if (
                        window.ViewerControls &&
                        window.ViewerControls.updateForRepresentation
                    ) {
                        window.ViewerControls.updateForRepresentation(
                            resolved.representationId
                        );
                    }
                    if (
                        window.EyecatcherDebug &&
                        window.EyecatcherDebug.updateForRepresentation
                    ) {
                        window.EyecatcherDebug.updateForRepresentation(
                            resolved.representationId
                        );
                    }
                    if (_deps.updateStats) _deps.updateStats();
                })
                .catch(function (e) {
                    console.error(e);
                    if (window.Toast && window.Toast.show) {
                        window.Toast.show(
                            "Add failed",
                            e.message || "Failed to compile",
                            "error"
                        );
                    }
                });
        });
    }

    window.PopulationLoader = {
        init: init,
        loadPopulation: loadPopulation,
        addToPopulation: addToPopulation,
    };
})();

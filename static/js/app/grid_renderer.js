/**
 * GridRenderer: builds and clears the pattern grid DOM; load and add population from stateless genomes.
 * Receives population and callbacks from app.js. Researchers change card layout or styling here or in CSS.
 *
 * Dependencies: window.PatternRenderer.createPatternCard, window.PopulationState, window.SubstrateAdapters, etc.
 * Exposes: init, clearGrid, renderGridFromPopulation, appendCardsToGrid, patternCardCallbacks, loadFromStatelessGenomes, addToGrid
 */
(function () {
    "use strict";

    var _deps = null;

    function clearGrid(ids) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (grid) grid.innerHTML = "";
    }

    function _notifySubstrateChange(substrateId) {
        window.ViewerControls.updateForSubstrate(substrateId);
        if (window.EyecatcherDebug && window.EyecatcherDebug.updateForSubstrate) {
            window.EyecatcherDebug.updateForSubstrate(substrateId);
        }
    }

    function _clearLoading() {
        if (_deps.showLoading) _deps.showLoading(false);
        window.PopulationState.dispatch({
            type: "SET_LOADING",
            payload: false,
        });
    }

    /**
     * Build card callbacks for one pattern (for PatternRenderer.createPatternCard).
     * @param {Object} pattern - { id, shader, nodes, connections, clicks }
     * @param {Object} callbacks - onShare, onNetwork, onSave, onFullscreen, onClick, onUnclick, onMouseEnter, onMouseLeave
     * @param {string} [substrateId] - current substrate id for adapter.preparePatternData
     */
    function patternCardCallbacks(pattern, callbacks, substrateId) {
        var c = callbacks || {};
        var opts = {
            pattern: pattern,
            onShare: c.onShare,
            onNetwork: c.onNetwork,
            onSave: c.onSave,
            onFullscreen: c.onFullscreen,
            onClick: c.onClick,
            onUnclick: c.onUnclick,
            onMouseEnter: c.onMouseEnter,
            onMouseLeave: c.onMouseLeave,
        };
        if (substrateId != null) opts.substrateId = substrateId;
        return opts;
    }

    /**
     * Render population into the grid and fill patternsMap (id -> { canvas, gl, program, positionBuffer, clicks }).
     * @param {Array} population - list of { id, shader, nodes, connections, clicks }
     * @param {Object} ids - { grid }
     * @param {Object} callbacks - same as for patternCardCallbacks
     * @param {Map} [patternsMap] - optional Map to fill; if not provided a new Map is created and returned
     * @param {string} [substrateId] - current substrate id for adapter.preparePatternData
     * @returns {Map} the patterns Map (same as patternsMap if provided)
     */
    function renderGridFromPopulation(
        population,
        ids,
        callbacks,
        patternsMap,
        substrateId
    ) {
        var map = patternsMap || new Map();
        map.clear();
        clearGrid(ids);
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (!grid || !population || !population.length) return map;

        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !PatternRenderer.createPatternCard) return map;

        population.forEach(function (pattern) {
            var result = PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern, callbacks, substrateId)
            );
            grid.appendChild(result.card);
            if (pattern.id !== undefined) {
                var pd = result.patternData;
                var entry = {
                    canvas: result.canvas,
                    gl: pd ? pd.gl : null,
                    program: pd ? pd.program : null,
                    positionBuffer: pd ? pd.positionBuffer : null,
                    clicks: pattern.clicks !== undefined ? pattern.clicks : 0,
                };
                if (pd && pd.caRule !== undefined) entry.caRule = pd.caRule;
                map.set(pattern.id, entry);
            }
        });
        return map;
    }

    /**
     * Append new pattern cards to the grid without clearing. Fills patternsMap with new entries.
     * @param {Array} population - list of { id, shader, nodes, connections, clicks }
     * @param {Object} ids - { grid }
     * @param {Object} callbacks - same as for patternCardCallbacks
     * @param {Map} patternsMap - existing Map to add to (mutated)
     * @param {string} [substrateId] - current substrate id for adapter.preparePatternData
     */
    function appendCardsToGrid(population, ids, callbacks, patternsMap, substrateId) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (!grid || !population || !population.length || !patternsMap) return;
        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !PatternRenderer.createPatternCard) return;
        population.forEach(function (pattern) {
            var result = PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern, callbacks, substrateId)
            );
            grid.appendChild(result.card);
            if (pattern.id !== undefined) {
                var pd = result.patternData;
                var entry = {
                    canvas: result.canvas,
                    gl: pd ? pd.gl : null,
                    program: pd ? pd.program : null,
                    positionBuffer: pd ? pd.positionBuffer : null,
                    clicks: pattern.clicks !== undefined ? pattern.clicks : 0,
                };
                if (pd && pd.caRule !== undefined) entry.caRule = pd.caRule;
                patternsMap.set(pattern.id, entry);
            }
        });
    }

    function loadFromStatelessGenomes(
        genomes,
        generationNum,
        saveToGenealogy,
        outputType,
        substrateId
    ) {
        if (!_deps || !genomes || !genomes.length) return Promise.resolve();
        var resolved = _deps.resolveAdapterAndOutput(outputType, substrateId, genomes);
        var resolvedOutputType = resolved.outputType;
        var resolvedSubstrateId = resolved.substrateId;
        var adapter = resolved.adapter;
        if (_deps.showLoading) _deps.showLoading(true);
        window.PopulationState.dispatch({
            type: "SET_LOADING",
            payload: true,
        });
        clearGrid(_deps.IDS);
        return window.SubstrateAdapters.getDisplayData(adapter, genomes, {
            colorMode: _deps.getColorMode(),
        })
            .then(function (displayResult) {
                var population = displayResult.population || [];
                var patternsMap = new Map();
                renderGridFromPopulation(
                    population,
                    _deps.IDS,
                    _deps.getGridCallbacks(),
                    patternsMap,
                    resolvedSubstrateId
                );
                var branchName = window.PopulationState.getState().branchName || "main";
                var parentId = window.PopulationState.getState().populationId;
                if (saveToGenealogy) {
                    if (generationNum === 0) {
                        parentId = null;
                        window.GenealogySync.syncCurrentPopulationIdToStorage(null);
                        var counter = window.GenealogySync.getGenealogyBranchCounter();
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
                        return pat ? pat.clicks || 0 : 0;
                    });
                    return window.GenealogySync.saveCurrentPopulationToGenealogy(
                        _deps.API_URL,
                        genomes,
                        generationNum,
                        branchName,
                        parentId,
                        fitnessData,
                        window.ApiClient.apiFetch,
                        resolvedSubstrateId
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
                            return { population, patternsMap };
                        });
                }
                return { population, patternsMap };
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
                        substrateId: resolvedSubstrateId,
                        outputType: resolvedOutputType,
                    },
                });
                _notifySubstrateChange(resolvedSubstrateId);
                var genEl = document.getElementById(_deps.IDS.genNum);
                if (genEl) genEl.textContent = generationNum;
                if (_deps.updateStats) _deps.updateStats();
            })
            .catch(function (e) {
                console.error(e);
                if (_deps.showGridError) {
                    _deps.showGridError(e.message || "Failed to compile", true);
                }
            })
            .finally(_clearLoading);
    }

    function addToGrid(genomes, outputTypeOverride) {
        if (!_deps || !genomes || !genomes.length) return Promise.resolve();
        var state = window.PopulationState.getState();
        var outputType =
            outputTypeOverride != null
                ? outputTypeOverride
                : state.outputType || "shader";
        var resolved = _deps.resolveAdapterAndOutput(
            outputType,
            state.substrateId,
            genomes
        );
        var adapter = resolved.adapter;
        var nextKey = 0;
        state.patterns.forEach(function (_, id) {
            nextKey = Math.max(nextKey, id + 1);
        });
        var payload = genomes.map(function (g) {
            var copy = Object.assign({}, g);
            copy.key = nextKey++;
            copy.clicks = 0;
            return copy;
        });
        if (_deps.showLoading) _deps.showLoading(true);
        window.PopulationState.dispatch({
            type: "SET_LOADING",
            payload: true,
        });
        return window.SubstrateAdapters.getDisplayData(adapter, payload, {
            colorMode: _deps.getColorMode(),
        })
            .then(function (displayResult) {
                var population = displayResult.population || [];
                appendCardsToGrid(
                    population,
                    _deps.IDS,
                    _deps.getGridCallbacks(),
                    state.patterns,
                    state.substrateId
                );
                window.PopulationState.dispatch({
                    type: "ADD_TO_GRID",
                    payload: {
                        genomes: payload,
                        population: population,
                        patternsMap: undefined,
                    },
                });
                _notifySubstrateChange(state.substrateId);
                if (_deps.updateStats) _deps.updateStats();
            })
            .catch(function (e) {
                console.error(e);
                window.Toast.show(
                    "Add failed",
                    e.message || "Failed to compile",
                    "error"
                );
            })
            .finally(_clearLoading);
    }

    function init(deps) {
        _deps = deps;
    }

    window.GridRenderer = {
        init: init,
        clearGrid: clearGrid,
        renderGridFromPopulation: renderGridFromPopulation,
        appendCardsToGrid: appendCardsToGrid,
        patternCardCallbacks: patternCardCallbacks,
        loadFromStatelessGenomes: loadFromStatelessGenomes,
        addToGrid: addToGrid,
    };
})();

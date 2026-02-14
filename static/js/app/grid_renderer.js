/**
 * GridRenderer: builds and clears the pattern grid DOM; load and add population from stateless genomes.
 * Receives population and callbacks from app.js. Researchers change card layout or styling here or in CSS.
 *
 * Dependencies: window.PatternRenderer.createPatternCard, window.PopulationState, window.SubstrateAdapters, etc.
 * Exposes: init, clearGrid, renderGridFromPopulation, appendCardsToGrid, patternCardCallbacks, loadFromStatelessGenomes, addToGrid
 */

/**
 * GridTopology: tracks which pattern is at which row/col position in the grid
 * and provides neighbor lookups. Used by the animation loop to pass neighbor
 * context to adapter lifecycle hooks (onBeforeRender, onAfterRender).
 *
 * Exposes: window.GridTopology.getPosition(patternId), getNeighbors(patternId),
 *   getAll(), getColumns(), rebuild(gridElement)
 */
(function () {
    "use strict";

    /** @type {Map<number|string, { row: number, col: number }>} */
    var _positions = new Map();
    var _columns = 0;

    /**
     * Rebuild the topology from the current grid DOM.
     * Call this after renderGridFromPopulation or appendCardsToGrid.
     * @param {HTMLElement} gridElement - The grid container element
     */
    function rebuild(gridElement) {
        _positions.clear();
        _columns = 0;
        if (!gridElement) return;

        var cards = gridElement.querySelectorAll(".pattern-card");
        if (!cards.length) return;

        // Detect number of columns from CSS grid layout
        var style = window.getComputedStyle(gridElement);
        var templateCols = style.getPropertyValue("grid-template-columns");
        if (templateCols && templateCols !== "none") {
            _columns = templateCols.split(/\s+/).filter(Boolean).length;
        }
        if (_columns === 0) {
            // Fallback: count cards in the first row by matching top offset
            var firstTop = cards[0].getBoundingClientRect().top;
            for (var c = 0; c < cards.length; c++) {
                if (cards[c].getBoundingClientRect().top !== firstTop) break;
                _columns++;
            }
        }
        if (_columns === 0) _columns = 1;

        for (var i = 0; i < cards.length; i++) {
            var id = cards[i].dataset.id;
            if (id !== undefined) {
                var numId = parseInt(id, 10);
                var key = isNaN(numId) ? id : numId;
                _positions.set(key, {
                    row: Math.floor(i / _columns),
                    col: i % _columns,
                });
            }
        }
    }

    /**
     * Get the grid position of a pattern.
     * @param {number|string} patternId
     * @returns {{ row: number, col: number } | null}
     */
    function getPosition(patternId) {
        return _positions.get(patternId) || null;
    }

    /**
     * Get the IDs of the four neighbors (top, bottom, left, right) of a pattern.
     * Returns null for edges where no neighbor exists.
     * @param {number|string} patternId
     * @returns {{ top: number|string|null, bottom: number|string|null, left: number|string|null, right: number|string|null } | null}
     */
    function getNeighbors(patternId) {
        var pos = _positions.get(patternId);
        if (!pos) return null;
        var result = { top: null, bottom: null, left: null, right: null };
        _positions.forEach(function (p, id) {
            if (p.col === pos.col && p.row === pos.row - 1) result.top = id;
            if (p.col === pos.col && p.row === pos.row + 1) result.bottom = id;
            if (p.row === pos.row && p.col === pos.col - 1) result.left = id;
            if (p.row === pos.row && p.col === pos.col + 1) result.right = id;
        });
        return result;
    }

    /**
     * Get all positions as a Map<patternId, { row, col }>.
     * @returns {Map}
     */
    function getAll() {
        return new Map(_positions);
    }

    /**
     * Get the current number of columns in the grid.
     * @returns {number}
     */
    function getColumns() {
        return _columns;
    }

    window.GridTopology = {
        rebuild: rebuild,
        getPosition: getPosition,
        getNeighbors: getNeighbors,
        getAll: getAll,
        getColumns: getColumns,
    };
})();

(function () {
    "use strict";

    var _deps = null;

    function clearGrid(ids) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (grid) grid.innerHTML = "";
        if (window.GridTopology) window.GridTopology.rebuild(null);
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

    function _buildPatternMapEntry(pattern, result) {
        var pd = result.patternData || {};
        var entry = {
            canvas: result.canvas,
            gl: pd.gl || null,
            program: pd.program || null,
            positionBuffer: pd.positionBuffer || null,
            clicks: pattern.clicks !== undefined ? pattern.clicks : 0,
            patternId: pattern.id,
        };
        if (pd.caRule !== undefined) entry.caRule = pd.caRule;
        if (pd.grid !== undefined) entry.grid = pd.grid;
        if (pd.toggleMask !== undefined) entry.toggleMask = pd.toggleMask;
        if (pattern.grid !== undefined) entry.grid = pattern.grid;
        for (var k in pd) {
            if (Object.prototype.hasOwnProperty.call(pd, k) && entry[k] === undefined) {
                entry[k] = pd[k];
            }
        }
        return entry;
    }

    function _appendPatternCards(
        population,
        grid,
        callbacks,
        patternsMap,
        substrateId
    ) {
        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !PatternRenderer.createPatternCard) return;
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({ substrateId: substrateId })
                : { adapter: null };
        var adapter = resolved.adapter;
        population.forEach(function (pattern) {
            var result = PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern, callbacks, substrateId)
            );
            grid.appendChild(result.card);
            var entry = _buildPatternMapEntry(pattern, result);
            if (adapter && typeof adapter.onSetup === "function") {
                adapter.onSetup(entry, entry.gl);
            }
            if (pattern.id !== undefined) {
                patternsMap.set(pattern.id, entry);
            }
        });
        if (adapter && typeof adapter.gridOverlap === "function") {
            var entries = Array.from(patternsMap.values());
            for (var i = 0; i < entries.length; i++) {
                var ei = entries[i];
                if (!ei.grid) continue;
                var bestId = null;
                var bestOverlap = 0;
                for (var j = 0; j < entries.length; j++) {
                    if (i === j) continue;
                    var ej = entries[j];
                    if (!ej.grid) continue;
                    var ov = adapter.gridOverlap(ei.grid, ej.grid);
                    if (ov > bestOverlap && ov < 1) {
                        bestOverlap = ov;
                        bestId = ej.patternId;
                    }
                }
                ei._mostSimilarId = bestId;
                ei._mostSimilarOverlap = bestOverlap;
            }
        }
    }

    /**
     * Render population into the grid and fill patternsMap (id -> { canvas, gl, program, positionBuffer, clicks }).
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
        _appendPatternCards(population, grid, callbacks, map, substrateId);
        if (window.GridTopology) window.GridTopology.rebuild(grid);
        return map;
    }

    /**
     * Append new pattern cards to the grid without clearing. Fills patternsMap with new entries.
     */
    function appendCardsToGrid(population, ids, callbacks, patternsMap, substrateId) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (!grid || !population || !population.length || !patternsMap) return;
        _appendPatternCards(population, grid, callbacks, patternsMap, substrateId);
        if (window.GridTopology) window.GridTopology.rebuild(grid);
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

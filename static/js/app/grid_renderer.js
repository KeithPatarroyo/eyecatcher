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
 */
(function () {
    "use strict";

    class GridTopology {
        constructor() {
            /** @type {Map<number|string, { row: number, col: number }>} */
            this._positions = new Map();
            this._columns = 0;
        }

        rebuild(gridElement) {
            this._positions.clear();
            this._columns = 0;
            if (!gridElement) return;

            var cards = gridElement.querySelectorAll(".pattern-card");
            if (!cards.length) return;

            var style = window.getComputedStyle(gridElement);
            var templateCols = style.getPropertyValue("grid-template-columns");
            if (templateCols && templateCols !== "none") {
                this._columns = templateCols.split(/\s+/).filter(Boolean).length;
            }
            if (this._columns === 0) {
                var firstTop = cards[0].getBoundingClientRect().top;
                for (var c = 0; c < cards.length; c++) {
                    if (cards[c].getBoundingClientRect().top !== firstTop) break;
                    this._columns++;
                }
            }
            if (this._columns === 0) this._columns = 1;

            for (var i = 0; i < cards.length; i++) {
                var id = cards[i].dataset.id;
                if (id !== undefined) {
                    var numId = parseInt(id, 10);
                    var key = isNaN(numId) ? id : numId;
                    this._positions.set(key, {
                        row: Math.floor(i / this._columns),
                        col: i % this._columns,
                    });
                }
            }
        }

        getPosition(patternId) {
            return this._positions.get(patternId) || null;
        }

        getNeighbors(patternId) {
            var pos = this._positions.get(patternId);
            if (!pos) return null;
            var result = { top: null, bottom: null, left: null, right: null };
            this._positions.forEach(function (p, id) {
                if (p.col === pos.col && p.row === pos.row - 1) result.top = id;
                if (p.col === pos.col && p.row === pos.row + 1) result.bottom = id;
                if (p.row === pos.row && p.col === pos.col - 1) result.left = id;
                if (p.row === pos.row && p.col === pos.col + 1) result.right = id;
            });
            return result;
        }

        getAll() {
            return new Map(this._positions);
        }

        getColumns() {
            return this._columns;
        }
    }

    window.GridTopology = new GridTopology();
})();

(function () {
    "use strict";

    class GridRenderer {
        constructor() {
            this._deps = null;
        }

        init(deps) {
            this._deps = deps;
        }

        clearGrid(ids) {
            var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
            if (grid) grid.innerHTML = "";
            window.GridTopology.rebuild(null);
        }

        _notifySubstrateChange(substrateId) {
            window.ViewerControls.updateForSubstrate(substrateId);
            if (window.EyecatcherDebug && window.EyecatcherDebug.updateForSubstrate) {
                window.EyecatcherDebug.updateForSubstrate(substrateId);
            }
        }

        patternCardCallbacks(pattern, callbacks, substrateId) {
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

        _buildPatternMapEntry(pattern, result) {
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
                if (
                    Object.prototype.hasOwnProperty.call(pd, k) &&
                    entry[k] === undefined
                ) {
                    entry[k] = pd[k];
                }
            }
            return entry;
        }

        _appendPatternCards(population, grid, callbacks, patternsMap, substrateId) {
            var PatternRenderer = window.PatternRenderer;
            if (!PatternRenderer || !PatternRenderer.createPatternCard) return;
            var adapter = window.SubstrateAdapters.safeResolve({
                substrateId: substrateId,
            }).adapter;
            var self = this;
            population.forEach(function (pattern) {
                var result = PatternRenderer.createPatternCard(
                    self.patternCardCallbacks(pattern, callbacks, substrateId)
                );
                grid.appendChild(result.card);
                var entry = self._buildPatternMapEntry(pattern, result);
                if (adapter) {
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

        renderGridFromPopulation(population, ids, callbacks, patternsMap, substrateId) {
            var map = patternsMap || new Map();
            map.clear();
            this.clearGrid(ids);
            var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
            if (!grid || !population || !population.length) return map;
            this._appendPatternCards(population, grid, callbacks, map, substrateId);
            window.GridTopology.rebuild(grid);
            return map;
        }

        appendCardsToGrid(population, ids, callbacks, patternsMap, substrateId) {
            var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
            if (!grid || !population || !population.length || !patternsMap) return;
            this._appendPatternCards(
                population,
                grid,
                callbacks,
                patternsMap,
                substrateId
            );
            window.GridTopology.rebuild(grid);
        }

        loadFromStatelessGenomes(
            genomes,
            generationNum,
            saveToGenealogy,
            outputType,
            substrateId
        ) {
            if (!this._deps || !genomes || !genomes.length) {
                return Promise.resolve();
            }
            var resolved = this._deps.resolveAdapterAndOutput(
                outputType,
                substrateId,
                genomes
            );
            var resolvedOutputType = resolved.outputType;
            var resolvedSubstrateId = resolved.substrateId;
            var adapter = resolved.adapter;
            var self = this;
            if (!adapter) {
                if (this._deps.showGridError) {
                    this._deps.showGridError(
                        "No adapter for substrate " +
                            (resolvedSubstrateId || "?") +
                            ". Check SubstrateConfig.",
                        false
                    );
                }
                if (this._deps.showLoading) this._deps.showLoading(false);
                window.PopulationState.dispatch({
                    type: "SET_LOADING",
                    payload: false,
                });
                return Promise.resolve();
            }
            return window.Utils.withLoading(function () {
                self.clearGrid(self._deps.IDS);
                return window.SubstrateAdapters.getDisplayData(adapter, genomes, {
                    colorMode: self._deps.getColorMode(),
                })
                    .then(function (displayResult) {
                        var population =
                            displayResult.population || displayResult.shaders || [];
                        if (!population.length) {
                            if (self._deps.showGridError) {
                                self._deps.showGridError(
                                    "No patterns returned from server.",
                                    true
                                );
                            }
                            return {
                                population: [],
                                patternsMap: new Map(),
                            };
                        }
                        var patternsMap = new Map();
                        self.renderGridFromPopulation(
                            population,
                            self._deps.IDS,
                            self._deps.getGridCallbacks(),
                            patternsMap,
                            resolvedSubstrateId
                        );
                        var branchName = window.PopulationState.branchName || "main";
                        var parentId = window.PopulationState.populationId;
                        if (saveToGenealogy) {
                            if (generationNum === 0) {
                                parentId = null;
                                window.GenealogySync.syncCurrentPopulationIdToStorage(
                                    null
                                );
                                var counter =
                                    window.GenealogySync.getGenealogyBranchCounter();
                                branchName =
                                    counter === 1 ? "main" : "branch-" + counter;
                                window.GenealogySync.setGenealogyBranchCounter(
                                    counter + 1
                                );
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
                                self._deps.API_URL,
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
                                    return {
                                        population: population,
                                        patternsMap: patternsMap,
                                    };
                                });
                        }
                        return { population: population, patternsMap: patternsMap };
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
                        self._notifySubstrateChange(resolvedSubstrateId);
                        var genEl = document.getElementById(self._deps.IDS.genNum);
                        if (genEl) genEl.textContent = generationNum;
                        if (self._deps.updateStats) self._deps.updateStats();
                    })
                    .catch(function (e) {
                        if (self._deps.showGridError) {
                            self._deps.showGridError(
                                e.message || "Failed to compile",
                                true
                            );
                        }
                    });
            });
        }

        addToGrid(genomes, outputTypeOverride) {
            if (!this._deps || !genomes || !genomes.length) return Promise.resolve();
            var outputType =
                outputTypeOverride != null
                    ? outputTypeOverride
                    : window.PopulationState.outputType || "shader";
            var resolved = this._deps.resolveAdapterAndOutput(
                outputType,
                window.PopulationState.substrateId,
                genomes
            );
            var adapter = resolved.adapter;
            var nextKey = 0;
            window.PopulationState.patterns.forEach(function (_, id) {
                nextKey = Math.max(nextKey, id + 1);
            });
            var payload = genomes.map(function (g) {
                var copy = Object.assign({}, g);
                copy.key = nextKey++;
                copy.clicks = 0;
                return copy;
            });
            var self = this;
            return window.Utils.withLoading(function () {
                return window.SubstrateAdapters.getDisplayData(adapter, payload, {
                    colorMode: self._deps.getColorMode(),
                })
                    .then(function (displayResult) {
                        var population = displayResult.population || [];
                        self.appendCardsToGrid(
                            population,
                            self._deps.IDS,
                            self._deps.getGridCallbacks(),
                            window.PopulationState.patterns,
                            window.PopulationState.substrateId
                        );
                        window.PopulationState.dispatch({
                            type: "ADD_TO_GRID",
                            payload: {
                                genomes: payload,
                                population: population,
                                patternsMap: undefined,
                            },
                        });
                        self._notifySubstrateChange(window.PopulationState.substrateId);
                        if (self._deps.updateStats) self._deps.updateStats();
                    })
                    .catch(function (e) {
                        console.error(e);
                        window.Toast.show(
                            "Add failed",
                            e.message || "Failed to compile",
                            "error"
                        );
                    });
            });
        }
    }

    window.GridRenderer = new GridRenderer();
})();

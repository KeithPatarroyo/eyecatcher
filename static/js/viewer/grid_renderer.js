/**
 * GridRenderer: builds and clears the pattern grid DOM (no load/add orchestration).
 * Receives population and callbacks from app. Load/add is in PopulationLoader.
 * Exposes: init, clearGrid, showGridError, renderGridFromPopulation, appendCardsToGrid, patternCardCallbacks.
 */

/**
 * GridTopology: tracks which pattern is at which row/col position in the grid
 * and provides neighbor lookups. Used by the animation loop for render context (grid position, neighbors).
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

            var cards = gridElement.querySelectorAll(".organism-card");
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

        showGridError(message, showRetry) {
            var IDS = this._deps && this._deps.IDS;
            if (!IDS) return;
            this.clearGrid(IDS);
            var grid = document.getElementById(IDS.grid);
            var tpl = document.getElementById(IDS.gridErrorTpl);
            if (!tpl || !tpl.content) {
                if (grid) {
                    var wrap = document.createElement("div");
                    wrap.className = "grid-error";
                    var msg = document.createElement("div");
                    msg.className = "grid-error__message";
                    msg.textContent = message;
                    wrap.appendChild(msg);
                    grid.appendChild(wrap);
                }
                if (this._deps.showLoading) this._deps.showLoading(false);
                return;
            }
            var devPort = window.DEFAULT_DEV_PORT || 5001;
            var localUrl = "http://localhost:" + devPort;
            var fragment = tpl.content.cloneNode(true);
            var root = fragment.querySelector(".grid-error");
            fragment.querySelector(".grid-error__message").textContent = message;
            var link = fragment.querySelector("#grid-error-link");
            if (link) {
                link.href = localUrl;
                link.textContent = localUrl;
            }
            if (showRetry) {
                var retryBtn = document.createElement("button");
                retryBtn.type = "button";
                retryBtn.className = "retry-btn";
                retryBtn.id = "grid-retry-btn";
                retryBtn.textContent = "New random population";
                root.appendChild(retryBtn);
            }
            this.clearGrid(IDS);
            grid = document.getElementById(IDS.grid);
            if (grid) grid.appendChild(fragment);
            if (this._deps.showLoading) this._deps.showLoading(false);
            if (showRetry) {
                var retryEl = document.getElementById(IDS.gridRetryBtn);
                if (retryEl) {
                    retryEl.onclick = function () {
                        window.PopulationUI.startNewRandomPopulation();
                    };
                }
            }
        }

        _notifyRepresentationChange(representationId) {
            window.ViewerControls.updateForRepresentation(representationId);
            if (
                window.EyecatcherDebug &&
                window.EyecatcherDebug.updateForRepresentation
            ) {
                window.EyecatcherDebug.updateForRepresentation(representationId);
            }
        }

        patternCardCallbacks(pattern, callbacks, representationId) {
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
            if (representationId != null) opts.representationId = representationId;
            return opts;
        }

        _buildPatternMapEntry(pattern, result) {
            var rt = result.runtime || {};
            var entry = {
                canvas: result.canvas,
                gl: rt.gl || null,
                program: rt.program || null,
                positionBuffer: rt.positionBuffer || null,
                fitness: pattern.fitness !== undefined ? pattern.fitness : 0,
                patternId: pattern.id,
            };
            if (rt.caRule !== undefined) entry.caRule = rt.caRule;
            if (rt.grid !== undefined) entry.grid = rt.grid;
            if (rt.toggleMask !== undefined) entry.toggleMask = rt.toggleMask;
            if (pattern.grid !== undefined) entry.grid = pattern.grid;
            for (var k in rt) {
                if (
                    Object.prototype.hasOwnProperty.call(rt, k) &&
                    entry[k] === undefined
                ) {
                    entry[k] = rt[k];
                }
            }
            return entry;
        }

        _appendPatternCards(
            population,
            grid,
            callbacks,
            patternsMap,
            representationId
        ) {
            var CardBuilder = window.CardBuilder;
            if (!CardBuilder || typeof CardBuilder.createCard !== "function") return;
            var self = this;
            population.forEach(function (pattern) {
                var result = CardBuilder.createCard(
                    self.patternCardCallbacks(pattern, callbacks, representationId)
                );
                grid.appendChild(result.card);
                var entry = self._buildPatternMapEntry(pattern, result);
                if (pattern.id !== undefined) {
                    patternsMap.set(pattern.id, entry);
                }
            });
        }

        renderGridFromPopulation(
            population,
            ids,
            callbacks,
            patternsMap,
            representationId
        ) {
            var map = patternsMap || new Map();
            map.clear();
            this.clearGrid(ids);
            var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
            if (!grid || !population || !population.length) return map;
            this._appendPatternCards(
                population,
                grid,
                callbacks,
                map,
                representationId
            );
            window.GridTopology.rebuild(grid);
            return map;
        }

        appendCardsToGrid(population, ids, callbacks, patternsMap, representationId) {
            var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
            if (!grid || !population || !population.length || !patternsMap) return;
            this._appendPatternCards(
                population,
                grid,
                callbacks,
                patternsMap,
                representationId
            );
            window.GridTopology.rebuild(grid);
        }
    }

    window.GridRenderer = new GridRenderer();
})();

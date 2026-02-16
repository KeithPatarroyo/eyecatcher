/**
 * GridRenderer: builds and clears the pattern grid DOM (no load/add orchestration).
 * Receives population and callbacks from app. Load/add is in PopulationLoader.
 * Exposes: init, clearGrid, showGridError, renderGridFromPopulation, appendCardsToGrid, patternCardCallbacks.
 */

/**
 * GridTopology: tracks which pattern is at which row/col position in the grid
 * and provides neighbor lookups. Used by the animation loop for render context (grid position, neighbors).
 */
(() => {
    "use strict";

    const toKey = (id) => {
        const n = parseInt(id, 10);
        return Number.isNaN(n) ? id : n;
    };

    const coordKey = (row, col) => `${row}:${col}`;

    class GridTopology {
        constructor() {
            /** Cache: patternId -> { row, col } derived from grid DOM (not canonical state). */
            this._positions = new Map();
            /** Cache: "row:col" -> patternId for neighbor lookup. */
            this._coordToId = new Map();
            this._columns = 0;
        }

        rebuild(gridElement) {
            this._positions.clear();
            this._coordToId.clear();
            this._columns = 0;
            if (!gridElement) return;

            const cards = gridElement.querySelectorAll(".organism-card");
            if (!cards.length) return;

            const style = window.getComputedStyle(gridElement);
            const templateCols = style.getPropertyValue("grid-template-columns");

            if (templateCols && templateCols !== "none") {
                this._columns = templateCols.split(/\s+/).filter(Boolean).length;
            }

            // Fallback: infer column count by scanning first row offsets
            if (this._columns === 0) {
                const firstTop = cards[0].getBoundingClientRect().top;
                for (let c = 0; c < cards.length; c++) {
                    if (cards[c].getBoundingClientRect().top !== firstTop) break;
                    this._columns++;
                }
            }

            if (this._columns === 0) this._columns = 1;

            for (let i = 0; i < cards.length; i++) {
                const idAttr = cards[i].dataset.id;
                if (idAttr === undefined) continue;

                const id = toKey(idAttr);
                const row = Math.floor(i / this._columns);
                const col = i % this._columns;

                this._positions.set(id, { row, col });
                this._coordToId.set(coordKey(row, col), id);
            }
        }

        getPosition(patternId) {
            return this._positions.get(patternId) || null;
        }

        getNeighbors(patternId) {
            const pos = this._positions.get(patternId);
            if (!pos) return null;

            const { row, col } = pos;
            return {
                top: this._coordToId.get(coordKey(row - 1, col)) ?? null,
                bottom: this._coordToId.get(coordKey(row + 1, col)) ?? null,
                left: this._coordToId.get(coordKey(row, col - 1)) ?? null,
                right: this._coordToId.get(coordKey(row, col + 1)) ?? null,
            };
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

(() => {
    "use strict";

    const getEl = (id) => (id ? document.getElementById(id) : null);

    const getGridEl = (ids) => getEl(ids?.grid);

    /** dataset.id is always string; coerce to number when numeric so getOrganism(id) matches state. */
    function parseCardId(value) {
        if (value == null || value === "") return undefined;
        const s = String(value);
        return /^\d+$/.test(s) ? parseInt(s, 10) : s;
    }

    function attachGridDelegatedListeners(grid, self) {
        if (!grid || grid.dataset.delegationBound === "true") return;
        grid.dataset.delegationBound = "true";

        DOM.delegate(grid, "click", ".organism-card", (ev, card) => {
            const isCanvasClick =
                ev.target?.nodeName === "CANVAS" &&
                card?.contains?.(ev.target) === true;
            if (isCanvasClick) {
                window.CardBuilder?.runCellInteraction?.(ev, card);
                return;
            }
            const id = parseCardId(card.dataset.id);
            if (id !== undefined) self._cardCallbacks?.onClick?.(id, card);
        });

        DOM.delegate(grid, "contextmenu", ".organism-card", (ev, card) => {
            ev.preventDefault();
            const isCanvasClick =
                ev.target?.nodeName === "CANVAS" &&
                card?.contains?.(ev.target) === true;
            if (isCanvasClick) {
                window.CardBuilder?.runCellInteraction?.(ev, card);
                return;
            }
            const id = parseCardId(card.dataset.id);
            if (id !== undefined) self._cardCallbacks?.onUnclick?.(id, card);
        });

        DOM.on(grid, "mouseover", (ev) => {
            const card = ev.target?.closest?.(".organism-card");
            if (!card || (ev.relatedTarget && card.contains(ev.relatedTarget))) return;
            const id = parseCardId(card.dataset.id);
            if (id !== undefined) self._cardCallbacks?.onMouseEnter?.(id);
        });

        DOM.on(grid, "mouseout", (ev) => {
            const card = ev.target?.closest?.(".organism-card");
            if (!card || (ev.relatedTarget && card.contains(ev.relatedTarget))) return;
            const id = parseCardId(card.dataset.id);
            if (id !== undefined) self._cardCallbacks?.onMouseLeave?.(id);
        });
    }

    const safeCall = (fn, ...args) => {
        try {
            return fn?.(...args);
        } catch (e) {
            console.warn("GridRenderer callback failed:", e);
            return undefined;
        }
    };

    class GridRenderer {
        constructor() {
            this._deps = null;
            /** Current callbacks for delegated card click/hover. */
            this._cardCallbacks = null;
        }

        init(deps) {
            this._deps = deps;
        }

        clearGrid(ids) {
            const grid = getGridEl(ids);
            if (grid) grid.innerHTML = "";
            window.GridTopology.rebuild(null);
        }

        showGridError(message, showRetry) {
            const IDS = this._deps?.IDS;
            if (!IDS) return;

            this.clearGrid(IDS);
            const grid = getEl(IDS.grid);
            const tpl = getEl(IDS.gridErrorTpl);

            const finish = () => safeCall(this._deps?.showLoading, false);

            if (!grid) return finish();

            // Simple fallback if the template is missing
            if (!tpl?.content) {
                const wrap = document.createElement("div");
                wrap.className = "grid-error";
                const msg = document.createElement("div");
                msg.className = "grid-error__message";
                msg.textContent = message;
                wrap.appendChild(msg);
                grid.appendChild(wrap);
                return finish();
            }

            const devPort = window.DEFAULT_DEV_PORT || 5001;
            const localUrl = `http://localhost:${devPort}`;

            const fragment = tpl.content.cloneNode(true);
            const root = fragment.querySelector(".grid-error");
            const msgEl = fragment.querySelector(".grid-error__message");
            if (msgEl) msgEl.textContent = message;

            const link = fragment.querySelector("#grid-error-link");
            if (link) {
                link.href = localUrl;
                link.textContent = localUrl;
            }

            if (showRetry && root) {
                const retryBtn = document.createElement("button");
                retryBtn.type = "button";
                retryBtn.className = "retry-btn";
                retryBtn.id = IDS.gridRetryBtn || "grid-retry-btn";
                retryBtn.textContent = "New random population";
                root.appendChild(retryBtn);
            }

            this.clearGrid(IDS);
            const freshGrid = getEl(IDS.grid);
            if (freshGrid) freshGrid.appendChild(fragment);

            finish();

            if (showRetry) {
                const retryEl = getEl(IDS.gridRetryBtn);
                if (retryEl) {
                    retryEl.onclick = () =>
                        window.PopulationUI?.startNewRandomPopulation?.();
                }
            }
        }

        _notifyRepresentationChange(representationId) {
            window.ViewerControls?.updateForRepresentation?.(representationId);
            window.EyecatcherDebug?.updateForRepresentation?.(representationId);
        }

        patternCardCallbacks(pattern, callbacks, representationId) {
            const c = callbacks || {};
            const opts = {
                pattern,
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
            const rt = result?.runtime || {};
            const entry = {
                canvas: result?.canvas ?? null,
                gl: rt.gl ?? null,
                program: rt.program ?? null,
                positionBuffer: rt.positionBuffer ?? null,
                fitness: pattern?.fitness ?? 0,
                patternId: pattern?.id,
            };

            // Prefer runtime-provided values, but keep pattern-provided grid as a fallback.
            if (rt.caRule !== undefined) entry.caRule = rt.caRule;
            if (rt.grid !== undefined) entry.grid = rt.grid;
            if (rt.toggleMask !== undefined) entry.toggleMask = rt.toggleMask;
            if (pattern?.grid !== undefined && entry.grid === undefined)
                entry.grid = pattern.grid;

            // Copy through any extra runtime keys without overwriting the explicit ones above.
            for (const k in rt) {
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
            const CardBuilder = window.CardBuilder;
            if (!CardBuilder || typeof CardBuilder.createCard !== "function") return;

            let displayFailureCount = 0;

            population.forEach((pattern, index) => {
                if (pattern?.id === undefined || pattern?.id === null) {
                    console.warn(
                        `appendCardsToGrid: pattern at index ${index} has no id, will not be in patternsMap`
                    );
                }

                const result = CardBuilder.createCard(
                    this.patternCardCallbacks(pattern, callbacks, representationId)
                );

                grid.appendChild(result.card);

                const entry = this._buildPatternMapEntry(pattern, result);
                if (pattern?.id !== undefined) patternsMap.set(pattern.id, entry);

                if (entry && !entry.gl) {
                    displayFailureCount++;
                    console.warn(
                        `appendCardsToGrid: card at index ${index} (id=${pattern?.id}) has no WebGL context, display may be broken`
                    );
                }
            });

            if (displayFailureCount > 0) {
                window.Toast?.show?.(
                    "Add from community",
                    `${displayFailureCount} organism(s) could not be displayed (missing rule or WebGL limit).`,
                    "error"
                );
            }
        }

        renderGridFromPopulation(
            population,
            ids,
            callbacks,
            patternsMap,
            representationId
        ) {
            const map = patternsMap || new Map();
            map.clear();

            this.clearGrid(ids);

            const grid = getGridEl(ids);
            if (!grid || !Array.isArray(population) || population.length === 0)
                return map;

            this._cardCallbacks = callbacks || null;
            attachGridDelegatedListeners(grid, this);

            this._appendPatternCards(
                population,
                grid,
                callbacks,
                map,
                representationId
            );
            this._patternsMap = map;
            window.GridTopology.rebuild(grid);

            return map;
        }

        appendCardsToGrid(population, ids, callbacks, patternsMap, representationId) {
            const grid = getGridEl(ids);
            if (
                !grid ||
                !Array.isArray(population) ||
                population.length === 0 ||
                !patternsMap
            )
                return;

            this._cardCallbacks = callbacks || this._cardCallbacks;
            attachGridDelegatedListeners(grid, this);

            this._appendPatternCards(
                population,
                grid,
                callbacks,
                patternsMap,
                representationId
            );
            if (!this._patternsMap) this._patternsMap = new Map();
            patternsMap.forEach((v, k) => this._patternsMap.set(k, v));
            window.GridTopology.rebuild(grid);
        }

        /** Get runtime (state) for a pattern id for FBO; tries number and string keys. */
        getRuntime(id) {
            if (!this._patternsMap) return null;
            const n = /^\d+$/.test(String(id)) ? parseInt(id, 10) : null;
            return (
                this._patternsMap.get(id) ??
                (n != null ? this._patternsMap.get(n) : null) ??
                this._patternsMap.get(String(id)) ??
                null
            );
        }
    }

    window.GridRenderer = new GridRenderer();
})();

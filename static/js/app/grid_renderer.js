/**
 * GridRenderer: builds and clears the pattern grid DOM. No state; receives population
 * and callbacks from app.js. Researchers change card layout or styling here or in CSS.
 *
 * Dependencies: window.PatternRenderer.createPatternCard
 * Exposes: GridRenderer.clearGrid, GridRenderer.renderGridFromPopulation, GridRenderer.patternCardCallbacks
 */
(function () {
    "use strict";

    function clearGrid(ids) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (grid) grid.innerHTML = "";
    }

    /**
     * Build card callbacks for one pattern (for PatternRenderer.createPatternCard).
     * @param {Object} pattern - { id, shader, nodes, connections, clicks }
     * @param {Object} callbacks - onShare, onNetwork, onSave, onFullscreen, onClick, onUnclick, onMouseEnter, onMouseLeave
     */
    function patternCardCallbacks(pattern, callbacks) {
        var c = callbacks || {};
        return {
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
    }

    /**
     * Render population into the grid and fill patternsMap (id -> { canvas, gl, program, positionBuffer, clicks }).
     * @param {Array} population - list of { id, shader, nodes, connections, clicks }
     * @param {Object} ids - { grid }
     * @param {Object} callbacks - same as for patternCardCallbacks
     * @param {Map} [patternsMap] - optional Map to fill; if not provided a new Map is created and returned
     * @returns {Map} the patterns Map (same as patternsMap if provided)
     */
    function renderGridFromPopulation(population, ids, callbacks, patternsMap) {
        var map = patternsMap || new Map();
        map.clear();
        clearGrid(ids);
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (!grid || !population || !population.length) return map;

        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !PatternRenderer.createPatternCard) return map;

        population.forEach(function (pattern) {
            var result = PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern, callbacks)
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
     */
    function appendCardsToGrid(population, ids, callbacks, patternsMap) {
        var grid = ids && ids.grid ? document.getElementById(ids.grid) : null;
        if (!grid || !population || !population.length || !patternsMap) return;
        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !PatternRenderer.createPatternCard) return;
        population.forEach(function (pattern) {
            var result = PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern, callbacks)
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

    window.GridRenderer = {
        clearGrid: clearGrid,
        renderGridFromPopulation: renderGridFromPopulation,
        appendCardsToGrid: appendCardsToGrid,
        patternCardCallbacks: patternCardCallbacks,
    };
})();

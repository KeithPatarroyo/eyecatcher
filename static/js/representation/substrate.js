/**
 * Substrate base class: contract for the physical body on which a phenotype is expressed.
 * Substrates (shader, grid, image) implement this interface; framework code uses it.
 * Only createDisplayElement and render are required; others have no-op defaults.
 *
 * @typedef {Object} Phenotype - From config: substrate, gridSize, stepShader, etc.
 * @typedef {Object} PatternPayload - From API: shader, grid, image, id, nodes, connections, etc.
 */
(function () {
    "use strict";

    class Substrate {
        /**
         * Create DOM element for display (canvas, img, etc.).
         * @param {Phenotype} phenotype - Declarative phenotype from config
         * @param {PatternPayload} patternPayload - Pattern data from compile/evaluate
         * @returns {{ element: HTMLElement, state: Object }} state is substrate-managed opaque data
         */
        createDisplayElement(phenotype, patternPayload) {
            var fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent = "Substrate not implemented";
            return { element: fallback, state: null };
        }

        /**
         * Initialize rendering resources after element is in DOM.
         * @param {Object} state - From createDisplayElement
         * @param {Phenotype} phenotype
         */
        setup(state, phenotype) {}

        /**
         * Clean up all resources.
         * @param {Object} state
         */
        teardown(state) {}

        /**
         * Translate environment signal values into substrate-specific params.
         * @param {Phenotype} phenotype
         * @param {Object} signalValues - signal id -> value
         * @returns {Object} params for render (e.g. uniforms, audio params)
         */
        buildParams(phenotype, signalValues) {
            return {};
        }

        /**
         * Render one frame or tick one step.
         * @param {Object} state
         * @param {Object} params - From buildParams
         * @param {Object} signalState - signal id -> boolean (enable toggles)
         */
        render(state, params, signalState) {}

        /**
         * Handle user interaction (click, drag). Optional.
         * @param {Object} state
         * @param {number} x - normalized 0-1
         * @param {number} y - normalized 0-1
         * @param {string} interactionType - "click" | "contextmenu"
         */
        handleInteraction(state, x, y, interactionType) {}
    }

    window.Substrate = Substrate;
})();

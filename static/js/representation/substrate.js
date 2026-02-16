/**
 * Substrate base class: contract for the physical body on which a phenotype is expressed.
 * Substrates (field, grid, image) implement this interface; framework code uses it.
 * Only createDisplayElement and render are required; others have no-op defaults.
 *
 * @typedef {Object} Phenotype - From config: substrate, gridSize, stepShader, etc.
 * @typedef {Object} PatternPayload - From API: rule (field), grid, image, id, nodes, connections, etc.
 */
(function () {
    "use strict";

    class Substrate {
        /**
         * Create a canvas element (optional helper for subclasses).
         * @param {number} [width=256]
         * @param {number} [height=256]
         * @returns {HTMLCanvasElement}
         */
        _createCanvas(width, height) {
            var canvas = document.createElement("canvas");
            canvas.className = "organism-canvas";
            canvas.width = width == null ? 256 : width;
            canvas.height = height == null ? 256 : height;
            return canvas;
        }

        /**
         * Create fallback div when rule/canvas is unavailable (optional helper for subclasses).
         * @param {string} [message=Substrate not implemented]
         * @returns {HTMLDivElement}
         */
        _createFallback(message) {
            var fallback = document.createElement("div");
            fallback.className = "organism-canvas-fallback";
            fallback.textContent = message || "Substrate not implemented";
            return fallback;
        }

        /**
         * Create DOM element for display (canvas, img, etc.).
         * @param {Phenotype} phenotype - Declarative phenotype from config
         * @param {PatternPayload} patternPayload - Pattern data from develop/express
         * @returns {{ element: HTMLElement, state: Object }} state is substrate-managed opaque data
         */
        createDisplayElement(phenotype, patternPayload) {
            return { element: this._createFallback(), state: null };
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
         * Default: map phenotype.sensorySystem.inputs to uniform names (u_<id>) and signal values.
         * @param {Phenotype} phenotype
         * @param {Object} signalValues - signal id -> value
         * @returns {Object} params for render (e.g. uniforms, audio params)
         */
        buildParams(phenotype, signalValues) {
            var out = {};
            var inputs =
                phenotype && phenotype.sensorySystem && phenotype.sensorySystem.inputs;
            if (inputs && Array.isArray(inputs) && signalValues) {
                inputs.forEach(function (inp) {
                    var uname = inp.uniform || (inp.id ? "u_" + inp.id : null);
                    if (uname && signalValues[inp.id] !== undefined) {
                        out[uname] = signalValues[inp.id];
                    }
                });
            }
            return out;
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

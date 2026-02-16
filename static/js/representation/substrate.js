/**
 * Substrate base class: contract for the physical body on which a phenotype is expressed.
 * Subclasses (field, grid, image) implement createDisplayElement() and render().
 */
class Substrate {
    _createCanvas(width = 256, height = 256) {
        const canvas = document.createElement("canvas");
        canvas.className = "organism-canvas";
        canvas.width = width;
        canvas.height = height;
        return canvas;
    }

    _createFallback(message = "Substrate not implemented") {
        const fallback = document.createElement("div");
        fallback.className = "organism-canvas-fallback";
        fallback.textContent = message;
        return fallback;
    }

    /**
     * Create DOM element for display (canvas/img/etc).
     * Return { element, state } where state is substrate-specific runtime (optional).
     */
    createDisplayElement(_phenotype, _patternPayload, _options) {
        return { element: this._createFallback(), state: null };
    }

    /** Optional hook called after createDisplayElement if state exists. */
    setup(_state, _phenotype) {}

    /** Map signalValues -> substrate params for rendering. Default: identity. */
    buildParams(_phenotype, signalValues) {
        return signalValues || {};
    }

    /** Render one frame into a runtime created by createDisplayElement. */
    render(_runtime, _params, _signalState) {}

    /** Optional per-cell interaction (grid substrate). */
    handleInteraction(_runtime, _x, _y, _interactionType) {}
}

window.Substrate = Substrate;

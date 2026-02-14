/**
 * RepresentationAdapter base class: default implementations for all optional adapter methods.
 * New representations extend RepresentationAdapter or use createRepresentationAdapter(config) to get
 * an instance with defaults; override only what differs.
 */
(function () {
    "use strict";

    class RepresentationAdapter {
        /**
         * @param {Object} config - id, outputType, isGenomeFormat required; plus any method overrides
         */
        constructor(config) {
            config = config || {};
            this.lifecycle = "frame";
            this.getMetaLabel = null;
            this.capabilities = {};
            this.hasSignalControls = false;
            for (var key in config) {
                if (Object.prototype.hasOwnProperty.call(config, key)) {
                    this[key] = config[key];
                }
            }
        }

        render() {}

        onSetup() {}

        onTeardown() {}

        onBeforeRender() {}

        onAfterRender() {}

        preparePatternData() {}

        buildUniforms() {
            return {};
        }

        getMetaIdPrefix() {
            return "ID: ";
        }

        getDisplayData(genomes, options) {
            var SA = window.RepresentationAdapters;
            if (!SA)
                return Promise.reject(
                    new Error("RepresentationAdapters not available")
                );
            if (this.outputType === "grid") {
                return SA.fetchViaEvaluate
                    ? SA.fetchViaEvaluate(genomes, options)
                    : Promise.reject(new Error("fetchViaEvaluate not available"));
            }
            return SA.fetchViaCompile
                ? SA.fetchViaCompile(genomes, options)
                : Promise.reject(new Error("fetchViaCompile not available"));
        }

        /**
         * Default: shader -> canvas via PatternRenderer.setupPattern; image -> img; else fallback.
         * Adapters can override for custom display (e.g. CA grid with toggle).
         */
        createDisplayElement(pattern, _options) {
            var PatternRenderer =
                typeof window !== "undefined" && window.PatternRenderer;
            if (!PatternRenderer || !pattern) {
                var fallback = document.createElement("div");
                fallback.className = "pattern-canvas-fallback";
                fallback.textContent = "Display not available";
                return { element: fallback, patternData: null };
            }
            var shader = pattern.shader;
            if (!shader) {
                if (pattern.image) {
                    var img = document.createElement("img");
                    img.className = "pattern-canvas pattern-image";
                    img.src = pattern.image;
                    img.width = 256;
                    img.height = 256;
                    img.alt = "Pattern " + (pattern.id != null ? pattern.id : "");
                    return { element: img, patternData: null };
                }
                var noShader = document.createElement("div");
                noShader.className = "pattern-canvas-fallback";
                noShader.textContent = "No shader";
                return { element: noShader, patternData: null };
            }
            var canvas = document.createElement("canvas");
            canvas.className = "pattern-canvas";
            canvas.width = 256;
            canvas.height = 256;
            var patternData = PatternRenderer.setupPattern(canvas, shader);
            if (!patternData || patternData.error) {
                var errEl = document.createElement("div");
                errEl.className = "pattern-canvas-fallback";
                errEl.textContent =
                    patternData && patternData.error
                        ? patternData.error
                        : "Shader error";
                return { element: errEl, patternData: null };
            }
            return { element: canvas, patternData: patternData };
        }

        supportsCellInteraction() {
            return typeof this.onCellInteraction === "function";
        }

        hasCapability(name) {
            return this.capabilities[name] !== false;
        }
    }

    /**
     * Create an adapter with default implementations. For backward compatibility.
     * @param {Object} overrides - id, outputType, isGenomeFormat required; plus any method overrides
     * @returns {RepresentationAdapter}
     */
    function createRepresentationAdapter(overrides) {
        return new RepresentationAdapter(overrides);
    }

    window.RepresentationAdapter = RepresentationAdapter;
    window.createRepresentationAdapter = createRepresentationAdapter;
})();

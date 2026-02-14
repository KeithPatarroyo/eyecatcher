/**
 * SubstrateAdapter base class: default implementations for all optional adapter methods.
 * New substrates extend SubstrateAdapter or use createSubstrateAdapter(config) to get
 * an instance with defaults; override only what differs.
 */
(function () {
    "use strict";

    class SubstrateAdapter {
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
            var SA = window.SubstrateAdapters;
            if (!SA)
                return Promise.reject(new Error("SubstrateAdapters not available"));
            if (this.outputType === "grid") {
                return SA.fetchViaEvaluate
                    ? SA.fetchViaEvaluate(genomes, options)
                    : Promise.reject(new Error("fetchViaEvaluate not available"));
            }
            return SA.fetchViaCompile
                ? SA.fetchViaCompile(genomes, options)
                : Promise.reject(new Error("fetchViaCompile not available"));
        }

        createDisplayElement() {
            var el = document.createElement("div");
            el.className = "pattern-canvas-fallback";
            el.textContent = "Display not available";
            return { element: el, patternData: null };
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
     * @returns {SubstrateAdapter}
     */
    function createSubstrateAdapter(overrides) {
        return new SubstrateAdapter(overrides);
    }

    window.SubstrateAdapter = SubstrateAdapter;
    window.createSubstrateAdapter = createSubstrateAdapter;
})();

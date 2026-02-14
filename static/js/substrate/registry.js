/**
 * Substrate adapter registry. Each substrate (dual_cppn, single_cppn, ca) can register
 * an adapter for render, preparePatternData, and import detection (isGenomeFormat).
 * Pattern renderer and app use getAdapter(substrateId) to delegate.
 * Single source for default resolution: use resolve() everywhere.
 *
 * ## Adapter interface
 *
 * @typedef {Object} SubstrateAdapter
 * @property {string} id - Substrate identifier (must match Python substrate.id)
 * @property {string} outputType - "shader" | "grid" | "image" | "audio" | ...
 * @property {string} [lifecycle] - "frame" (default): per-frame render via animation loop; "self-managed": adapter owns update (e.g. audio playback)
 * @property {function(Array, Object): Promise<{ population: Array }>} [getDisplayData] - Fetch display-ready data for genomes; required for agnostic flow, fallback exists for BACKWARDS_COMPAT
 * @property {function(Object, Object): { element: HTMLElement, patternData: Object|null }} [createDisplayElement] - Create the DOM element for one pattern; required for agnostic flow, fallback exists for BACKWARDS_COMPAT
 * @property {function(Object): boolean} isGenomeFormat - Return true if a genome object belongs to this substrate
 * @property {boolean} [hasSignalControls] - Whether to show signal toggle checkboxes (default false)
 * @property {{ save: boolean, network: boolean, timeOutput: boolean, adjustWeight: boolean }} [capabilities]
 * @property {function(Object, Object, Object): void} render - Draw one frame. Args: (patternData, uniformValues, signalState)
 * @property {function(Object, Object?): Object} [buildUniforms] - Convert signal-id-keyed values to uniform-name-keyed values; optional second arg is RenderContext for grid/neighbor uniforms
 * @property {function(Object, Object): void} [preparePatternData] - Store substrate-specific fields on patternData after setup
 * @property {function(Object): string} [getMetaLabel] - Return a custom info label for the pattern card
 * @property {function(): string} [getMetaIdPrefix] - Return label prefix before id (e.g. "Pattern " or "ID: "); default "ID: "
 * @property {function(Object, WebGL2RenderingContext): void} [onSetup] - Called once after WebGL setup (create FBOs, textures)
 * @property {function(Object, RenderContext): void} [onBeforeRender] - Called before each frame's render()
 * @property {function(Object, RenderContext): void} [onAfterRender] - Called after each frame's render()
 * @property {function(Object, WebGL2RenderingContext): void} [onTeardown] - Called on pattern removal (cleanup)
 * @property {function(Object, number, number, string): void} [onCellInteraction] - Pixel-level click. Args: (patternData, x, y, type) where x,y are 0-1 normalized and type is "click"|"contextmenu"
 *
 * @typedef {Object} RenderContext
 * @property {WebGL2RenderingContext} gl - The pattern's WebGL context
 * @property {HTMLCanvasElement} canvas - The pattern's canvas element
 * @property {{ row: number, col: number }|null} gridPosition - Position in the grid (from GridTopology)
 * @property {{ top: string|null, bottom: string|null, left: string|null, right: string|null }|null} neighbors - Neighbor pattern IDs (from GridTopology)
 * @property {number} frameCount - Animation frame counter
 * @property {number} deltaTime - Seconds since last frame
 */
(function () {
    "use strict";

    /** Single source for default substrate id when no config is present. */
    var DEFAULT_SUBSTRATE_ID = "dual_cppn";

    var DEFAULT_RESOLUTION = {
        outputType: "shader",
        substrateId: DEFAULT_SUBSTRATE_ID,
    };
    window.__eyecatcherDefaultResolution = {
        outputType: "shader",
        substrateId: DEFAULT_SUBSTRATE_ID,
        adapter: null,
    };

    const adaptersById = {};

    function register(adapter) {
        if (adapter && adapter.id) {
            adaptersById[adapter.id] = adapter;
        }
    }

    function getAdapter(substrateId) {
        if (!substrateId) return null;
        return adaptersById[substrateId] || null;
    }

    /**
     * Find adapter whose isGenomeFormat(genome) returns true. First match wins.
     * Order follows SubstrateConfig so that dual genomes match dual first.
     */
    function findAdapterByGenome(genome) {
        var config = window.SubstrateConfig;
        var order =
            config && Array.isArray(config)
                ? config.map(function (e) {
                      return e.id;
                  })
                : [DEFAULT_SUBSTRATE_ID, "single_cppn", "ca"];
        for (var i = 0; i < order.length; i++) {
            var adapter = adaptersById[order[i]];
            if (adapter && adapter.isGenomeFormat && adapter.isGenomeFormat(genome)) {
                return adapter;
            }
        }
        return null;
    }

    /**
     * Infer outputType and substrateId from genomes (for load/import when not stored).
     * @param {Array} genomes
     * @returns {{ outputType: string, substrateId: string }}
     */
    function getDefaultResolution() {
        return window.EvolutionConfig && window.EvolutionConfig.getDefaultResolution
            ? window.EvolutionConfig.getDefaultResolution()
            : DEFAULT_RESOLUTION;
    }

    /**
     * Default substrate id (single source for fallbacks). Uses EvolutionConfig after mergeFromServer.
     * @returns {string}
     */
    function getDefaultSubstrateId() {
        var res = getDefaultResolution();
        return res ? res.substrateId : DEFAULT_SUBSTRATE_ID;
    }

    /**
     * Safe resolve: use from any script. If SubstrateAdapters not yet loaded, returns default.
     * @param {{ outputType?: string, substrateId?: string, genomes?: Array }} opts
     * @returns {{ outputType: string, substrateId: string, adapter: Object|null }}
     */
    function safeResolve(opts) {
        var SA = window.SubstrateAdapters;
        if (SA && SA.resolve) {
            return SA.resolve(opts || {});
        }
        return {
            outputType: DEFAULT_RESOLUTION.outputType,
            substrateId: DEFAULT_RESOLUTION.substrateId,
            adapter: null,
        };
    }

    function resolveFromGenomes(genomes) {
        if (!genomes || !genomes.length) {
            return getDefaultResolution();
        }
        var adapter = findAdapterByGenome(genomes[0]);
        return adapter
            ? { outputType: adapter.outputType, substrateId: adapter.id }
            : getDefaultResolution();
    }

    /**
     * Single entry point to resolve adapter, outputType, and substrateId from options.
     * Use this instead of duplicating resolveForLoad/getDefaultResolution logic.
     * @param {{ outputType?: string, substrateId?: string, genomes?: Array }} opts
     * @returns {{ outputType: string, substrateId: string, adapter: Object|null }}
     */
    function resolve(opts) {
        return resolveForLoad(opts || {});
    }

    /**
     * Resolve outputType, substrateId, and adapter from a load payload (pop or state).
     * @param {{ outputType?: string, substrateId?: string, genomes?: Array }} pop
     * @returns {{ outputType: string, substrateId: string, adapter: Object|null }}
     */
    function resolveForLoad(pop) {
        if (!pop) pop = {};
        var adapter = null;
        if (pop.substrateId) {
            adapter = getAdapter(pop.substrateId);
        }
        if (!adapter && pop.genomes && pop.genomes.length) {
            var r = resolveFromGenomes(pop.genomes);
            adapter = getAdapter(r.substrateId);
        }
        if (!adapter) {
            var def = getDefaultResolution();
            adapter = getAdapter(def.substrateId);
        }
        var defRes = getDefaultResolution();
        return {
            outputType:
                (adapter && adapter.outputType) || pop.outputType || defRes.outputType,
            substrateId:
                (adapter && adapter.id) || pop.substrateId || defRes.substrateId,
            adapter: adapter,
        };
    }

    /**
     * Utility: fetch display data via /api/compile (for shader representations).
     * @param {Array} genomes - Genome objects
     * @param {Object} options - { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function fetchViaCompile(genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var compData = await ApiClient.compile(genomes, options && options.colorMode);
        return { population: compData.shaders || [] };
    }

    /**
     * Utility: fetch display data via /api/evaluate (for grid/other representations).
     * @param {Array} genomes - Genome objects
     * @param {Object} _options - Unused for evaluate
     * @returns {Promise<{ population: Array }>}
     */
    async function fetchViaEvaluate(genomes, _options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var evalData = await ApiClient.evaluate(genomes);
        var results = evalData.results || [];
        if (typeof performance !== "undefined") {
            window.CA_ANIMATION_START_TIME = performance.now();
        }
        return {
            population: results.map(function (r) {
                return {
                    id: r.id,
                    image: r.image,
                    shader: r.shader,
                    grid: r.grid,
                    nodes: r.nodes !== undefined ? r.nodes : 0,
                    connections: r.connections !== undefined ? r.connections : 0,
                    clicks: r.clicks !== undefined ? r.clicks : 0,
                };
            }),
        };
    }

    /**
     * BACKWARDS_COMPAT: Default getDisplayData when adapter does not implement getDisplayData.
     * Prefer adapter.getDisplayData (e.g. using fetchViaCompile/fetchViaEvaluate) and remove this fallback in a future cleanup.
     */
    async function defaultGetDisplayData(adapter, genomes, options) {
        var a = adapter || getDefaultResolution();
        if (a.outputType === "grid") {
            return fetchViaEvaluate(genomes, options);
        }
        return fetchViaCompile(genomes, options);
    }

    /**
     * Fetch display data for genomes. Uses adapter.getDisplayData when present; otherwise BACKWARDS_COMPAT fallback.
     * @param {Object} adapter - Adapter (from getAdapter or resolveFromGenomes)
     * @param {Array} genomes - Genome objects
     * @param {Object} options - { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function getDisplayData(adapter, genomes, options) {
        var fn = adapter && adapter.getDisplayData;
        if (fn) {
            return fn.call(adapter, genomes, options);
        }
        return defaultGetDisplayData(adapter, genomes, options);
    }

    var SubstrateAdapters = {
        register: register,
        getAdapter: getAdapter,
        findAdapterByGenome: findAdapterByGenome,
        resolve: resolve,
        safeResolve: safeResolve,
        resolveFromGenomes: resolveFromGenomes,
        resolveForLoad: resolveForLoad,
        getDefaultResolution: getDefaultResolution,
        getDefaultSubstrateId: getDefaultSubstrateId,
        getDisplayData: getDisplayData,
        fetchViaCompile: fetchViaCompile,
        fetchViaEvaluate: fetchViaEvaluate,
    };

    window.SubstrateAdapters = SubstrateAdapters;

    function buildIsGenomeFormatFromConfig(entry) {
        var genomeKeys = entry.genomeKeys || [];
        var excludeKeys = entry.excludeKeys || [];
        return function (obj) {
            if (!obj) return false;
            for (var i = 0; i < genomeKeys.length; i++) {
                var k = genomeKeys[i];
                if (k === "rule") {
                    if (typeof obj.rule !== "number") return false;
                } else if (!obj[k]) return false;
            }
            for (var j = 0; j < excludeKeys.length; j++) {
                if (obj[excludeKeys[j]]) return false;
            }
            return true;
        };
    }

    var defaultCapabilities = {
        save: true,
        network: true,
        timeOutput: false,
        adjustWeight: false,
    };

    function mergeCapabilities(entry) {
        var caps = entry && entry.capabilities;
        if (!caps) return defaultCapabilities;
        return {
            save: caps.save !== false,
            network: caps.network !== false,
            timeOutput: caps.timeOutput === true,
            adjustWeight: caps.adjustWeight !== false,
        };
    }

    var config = window.SubstrateConfig;
    if (config && Array.isArray(config) && window.createCppnAdapter) {
        config.forEach(function (entry) {
            var isGenomeFormat = buildIsGenomeFormatFromConfig(entry);
            var capabilities = mergeCapabilities(entry);
            if (entry.outputType === "shader") {
                var cppnAdapter = window.createCppnAdapter({
                    id: entry.id,
                    outputType: entry.outputType,
                    isGenomeFormat: isGenomeFormat,
                    hasSignalControls: entry.hasSignalControls !== false,
                });
                cppnAdapter.capabilities = capabilities;
                register(cppnAdapter);
            } else {
                register({
                    id: entry.id,
                    outputType: entry.outputType,
                    lifecycle: "frame",
                    isGenomeFormat: isGenomeFormat,
                    hasSignalControls: entry.hasSignalControls !== false,
                    capabilities: capabilities,
                });
            }
        });
    }
})();

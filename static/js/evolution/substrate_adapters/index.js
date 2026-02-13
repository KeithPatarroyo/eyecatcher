/**
 * Substrate adapter registry. Each substrate (dual_cppn, single_cppn, ca) can register
 * an adapter for render, preparePatternData, and import detection (isGenomeFormat).
 * Pattern renderer and app use getAdapter(substrateId) to delegate.
 */
(function () {
    "use strict";

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
     * Order: dual_cppn, single_cppn, ca so that dual genomes match dual first.
     */
    function findAdapterByGenome(genome) {
        const order = ["dual_cppn", "single_cppn", "ca"];
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
    function resolveFromGenomes(genomes) {
        if (!genomes || !genomes.length) {
            return {
                outputType: "shader",
                substrateId:
                    (window.EvolutionConfig &&
                        window.EvolutionConfig.DEFAULT_SUBSTRATE_ID) ||
                    "dual_cppn",
            };
        }
        var adapter = findAdapterByGenome(genomes[0]);
        return adapter
            ? { outputType: adapter.outputType, substrateId: adapter.id }
            : {
                  outputType: "shader",
                  substrateId:
                      (window.EvolutionConfig &&
                          window.EvolutionConfig.DEFAULT_SUBSTRATE_ID) ||
                      "dual_cppn",
              };
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
            adapter = getAdapter(
                (window.EvolutionConfig &&
                    window.EvolutionConfig.DEFAULT_SUBSTRATE_ID) ||
                    "dual_cppn"
            );
        }
        return {
            outputType: (adapter && adapter.outputType) || pop.outputType || "shader",
            substrateId:
                (adapter && adapter.id) ||
                pop.substrateId ||
                (window.EvolutionConfig &&
                    window.EvolutionConfig.DEFAULT_SUBSTRATE_ID) ||
                "dual_cppn",
            adapter: adapter,
        };
    }

    /**
     * Default getDisplayData: grid -> evaluate, shader -> compile.
     * Adapters can override with custom logic.
     * @param {Object} adapter - Adapter with outputType
     * @param {Array} genomes - Genome objects
     * @param {Object} options - { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function defaultGetDisplayData(adapter, genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        if (adapter.outputType === "grid") {
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
                        rule: r.rule,
                        nodes: 0,
                        connections: 0,
                        clicks: 0,
                    };
                }),
            };
        }
        var compData = await ApiClient.compile(genomes, options && options.colorMode);
        return { population: compData.shaders || [] };
    }

    /**
     * Fetch display data for genomes using adapter (evaluate for grid, compile for shader).
     * @param {Object} adapter - Adapter (from getAdapter or resolveFromGenomes)
     * @param {Array} genomes - Genome objects
     * @param {Object} options - { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function getDisplayData(adapter, genomes, options) {
        var fn = adapter && adapter.getDisplayData;
        return fn
            ? fn(genomes, options)
            : defaultGetDisplayData(
                  adapter || { outputType: "shader" },
                  genomes,
                  options
              );
    }

    var SubstrateAdapters = {
        register: register,
        getAdapter: getAdapter,
        findAdapterByGenome: findAdapterByGenome,
        resolveFromGenomes: resolveFromGenomes,
        resolveForLoad: resolveForLoad,
        getDisplayData: getDisplayData,
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

    var config = window.SubstrateAdapterConfig;
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
                    isGenomeFormat: isGenomeFormat,
                    hasSignalControls: entry.hasSignalControls !== false,
                    capabilities: capabilities,
                });
            }
        });
    }
})();

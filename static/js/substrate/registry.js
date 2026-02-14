/**
 * Substrate adapter registry. Each substrate (dual_cppn, single_cppn, ca) can register
 * an adapter. Pattern renderer and app use getAdapter(substrateId) to delegate.
 * Single source for default resolution: use resolve() everywhere.
 *
 * @typedef {Object} SubstrateAdapter
 * @typedef {Object} RenderContext
 */
(function () {
    "use strict";

    var DEFAULT_SUBSTRATE_ID = "dual_cppn";
    var DEFAULT_RESOLUTION = {
        outputType: "shader",
        substrateId: DEFAULT_SUBSTRATE_ID,
    };

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

    class SubstrateRegistry {
        constructor() {
            this._adaptersById = {};
            window.__eyecatcherDefaultResolution = {
                outputType: "shader",
                substrateId: DEFAULT_SUBSTRATE_ID,
                adapter: null,
            };
            this._bootstrapFromConfig();
        }

        _bootstrapFromConfig() {
            var config = window.SubstrateConfig;
            if (config && Array.isArray(config) && window.createCppnAdapter) {
                var self = this;
                config.forEach(function (entry) {
                    var isGenomeFormat = buildIsGenomeFormatFromConfig(entry);
                    var capabilities = mergeCapabilities(entry);
                    if (entry.adapterFactory === "cppn") {
                        var cppnAdapter = window.createCppnAdapter({
                            id: entry.id,
                            outputType: entry.outputType,
                            isGenomeFormat: isGenomeFormat,
                            hasSignalControls: entry.hasSignalControls !== false,
                        });
                        cppnAdapter.capabilities = capabilities;
                        self.register(cppnAdapter);
                    } else if (window.createSubstrateAdapter) {
                        self.register(
                            window.createSubstrateAdapter({
                                id: entry.id,
                                outputType: entry.outputType,
                                lifecycle: "frame",
                                isGenomeFormat: isGenomeFormat,
                                hasSignalControls: entry.hasSignalControls !== false,
                                capabilities: capabilities,
                            })
                        );
                    } else {
                        self.register({
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
        }

        register(adapter) {
            if (!adapter || !adapter.id) return;
            this._adaptersById[adapter.id] = adapter;
        }

        getAdapter(substrateId) {
            if (!substrateId) return null;
            return this._adaptersById[substrateId] || null;
        }

        findAdapterByGenome(genome) {
            var config = window.SubstrateConfig;
            var order =
                config && Array.isArray(config)
                    ? config.map(function (e) {
                          return e.id;
                      })
                    : [DEFAULT_SUBSTRATE_ID, "single_cppn", "ca"];
            for (var i = 0; i < order.length; i++) {
                var adapter = this._adaptersById[order[i]];
                if (
                    adapter &&
                    adapter.isGenomeFormat &&
                    adapter.isGenomeFormat(genome)
                ) {
                    return adapter;
                }
            }
            return null;
        }

        getDefaultResolution() {
            return window.EvolutionConfig && window.EvolutionConfig.getDefaultResolution
                ? window.EvolutionConfig.getDefaultResolution()
                : DEFAULT_RESOLUTION;
        }

        getDefaultSubstrateId() {
            var res = this.getDefaultResolution();
            return res ? res.substrateId : DEFAULT_SUBSTRATE_ID;
        }

        safeResolve(opts) {
            return this.resolve(opts || {});
        }

        resolveFromGenomes(genomes) {
            if (!genomes || !genomes.length) {
                return this.getDefaultResolution();
            }
            var adapter = this.findAdapterByGenome(genomes[0]);
            return adapter
                ? { outputType: adapter.outputType, substrateId: adapter.id }
                : this.getDefaultResolution();
        }

        resolve(opts) {
            return this.resolveForLoad(opts || {});
        }

        resolveForLoad(pop) {
            if (!pop) pop = {};
            var adapter = null;
            if (pop.substrateId) {
                adapter = this.getAdapter(pop.substrateId);
            }
            if (!adapter && pop.genomes && pop.genomes.length) {
                var r = this.resolveFromGenomes(pop.genomes);
                adapter = this.getAdapter(r.substrateId);
            }
            if (!adapter) {
                var def = this.getDefaultResolution();
                adapter = this.getAdapter(def.substrateId);
            }
            var defRes = this.getDefaultResolution();
            return {
                outputType:
                    (adapter && adapter.outputType) ||
                    pop.outputType ||
                    defRes.outputType,
                substrateId:
                    (adapter && adapter.id) || pop.substrateId || defRes.substrateId,
                adapter: adapter,
            };
        }

        /**
         * Resolve adapter for the current population (from PopulationState).
         * @returns {Object|null} Current adapter or null
         */
        currentAdapter() {
            var state = window.PopulationState.getState();
            return this.safeResolve({ substrateId: state.substrateId }).adapter;
        }

        /**
         * Resolve adapter and output type from a list of genomes.
         * @param {Array} genomes
         * @returns {{ adapter: Object|null, outputType: string, substrateId: string }}
         */
        resolveForGenomes(genomes) {
            return this.resolveForLoad(
                genomes && genomes.length ? { genomes: genomes } : {}
            );
        }

        async fetchViaCompile(genomes, options) {
            var ApiClient = window.ApiClient;
            if (!ApiClient) throw new Error("ApiClient not available");
            var compData = await ApiClient.compile(
                genomes,
                options && options.colorMode
            );
            return { population: compData.shaders || [] };
        }

        async fetchViaEvaluate(genomes, _options) {
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

        async getDisplayData(adapter, genomes, options) {
            return adapter.getDisplayData(genomes, options);
        }
    }

    window.SubstrateAdapters = new SubstrateRegistry();
})();

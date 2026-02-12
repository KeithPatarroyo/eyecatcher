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
            return { outputType: "shader", substrateId: "dual_cppn" };
        }
        var adapter = findAdapterByGenome(genomes[0]);
        return adapter
            ? { outputType: adapter.outputType, substrateId: adapter.id }
            : { outputType: "shader", substrateId: "dual_cppn" };
    }

    var SubstrateAdapters = {
        register: register,
        getAdapter: getAdapter,
        findAdapterByGenome: findAdapterByGenome,
        resolveFromGenomes: resolveFromGenomes,
    };

    if (typeof window !== "undefined") {
        window.SubstrateAdapters = SubstrateAdapters;
    }

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

    var config = typeof window !== "undefined" && window.SubstrateAdapterConfig;
    if (config && Array.isArray(config) && window.createCppnAdapter) {
        config.forEach(function (entry) {
            var isGenomeFormat = buildIsGenomeFormatFromConfig(entry);
            if (entry.outputType === "shader") {
                register(
                    window.createCppnAdapter({
                        id: entry.id,
                        outputType: entry.outputType,
                        isGenomeFormat: isGenomeFormat,
                        hasSignalControls: entry.hasSignalControls !== false,
                    })
                );
            } else {
                register({
                    id: entry.id,
                    outputType: entry.outputType,
                    isGenomeFormat: isGenomeFormat,
                    hasSignalControls: entry.hasSignalControls !== false,
                });
            }
        });
    } else if (typeof window !== "undefined" && window.createCppnAdapter) {
        register(
            window.createCppnAdapter({
                id: "dual_cppn",
                outputType: "shader",
                isGenomeFormat: function (obj) {
                    return obj && obj.visual && obj.time_signal;
                },
                hasSignalControls: true,
            })
        );
        register(
            window.createCppnAdapter({
                id: "single_cppn",
                outputType: "shader",
                isGenomeFormat: function (obj) {
                    return obj && obj.visual && !obj.time_signal;
                },
                hasSignalControls: false,
            })
        );
    }
})();

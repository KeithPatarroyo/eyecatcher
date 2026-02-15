/**
 * Display data fetching: develop (rule) and express (image/grid) via ApiClient.
 * No state, no DOM. Use from grid load, append, community preview, genealogy thumbnails.
 * Depends on window.ApiClient.
 */
(function () {
    "use strict";

    async function developGenomes(genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var compData = await ApiClient.develop(genomes, options && options.colorMode);
        return { population: compData.rules || [] };
    }

    async function expressGenomes(genomes, _options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var evalData = await ApiClient.express(genomes);
        var results = evalData.results || [];
        if (typeof performance !== "undefined") {
            window.CA_ANIMATION_START_TIME = performance.now();
        }
        return {
            population: results.map(function (r) {
                return {
                    id: r.id,
                    image: r.image,
                    rule: r.rule,
                    grid: r.grid,
                    nodes: r.nodes !== undefined ? r.nodes : 0,
                    connections: r.connections !== undefined ? r.connections : 0,
                    fitness: r.fitness !== undefined ? r.fitness : 0,
                };
            }),
        };
    }

    /**
     * Fetch display data for the given representation and genomes.
     * Routes to develop (rule) or express (image/grid) based on representation.phenotype.substrate.type.
     * @param {Object} representation - { phenotype: { substrate: { type } }, ... }
     * @param {Array} genomes
     * @param {Object} [options] - e.g. { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function fetchDisplayData(representation, genomes, options) {
        var substrate =
            (representation &&
                representation.phenotype &&
                representation.phenotype.substrate) ||
            "image";
        var substrateType =
            typeof substrate === "string"
                ? substrate
                : (substrate && substrate.type) || "image";
        if (substrateType === "field") {
            return developGenomes(genomes, options);
        }
        return expressGenomes(genomes, options);
    }

    window.DisplayFetcher = {
        developGenomes: developGenomes,
        expressGenomes: expressGenomes,
        fetchDisplayData: fetchDisplayData,
    };
})();
